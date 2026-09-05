"""PR Review Orchestrator — central coordinator for GitHub PR scanning and review.

Flow:
  webhook event
    → idempotency check
    → fetch PR + changed files
    → LeakGuard deterministic scan (changed Python files only)
    → risk score (deterministic)
    → AI explanations (explanatory only, no classification authority)
    → post GitHub review
    → store results in DB
    → audit trail

SECURITY:
  - Customer code is NEVER executed — only AST-parsed by LeakGuard engine
  - AI cannot modify classifications or risk scores
  - GitHub tokens never logged or exposed
"""
import os
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.analysis.engine import AnalysisEngine
from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification

from packages.github.client import GitHubClient, GitHubAPIError
from packages.github.auth import get_auth_provider
from packages.github.services.pull_request import GitHubPullRequestService, PRFile
from packages.github.services.review import GitHubReviewService, InlineComment
from packages.github.services.webhook import PullRequestWebhookEvent

from services.github_pr.risk_scorer import PRRiskScorer
from services.github_pr.inline_mapper import InlineCommentMapper
from services.github_pr.comment_builder import PRCommentBuilder

from services.ai.redactor import SecretRedactor


class PRReviewOrchestrator:
    """Orchestrates the full PR review pipeline from webhook event to GitHub comment."""

    def __init__(
        self,
        pr_service: Optional[GitHubPullRequestService] = None,
        review_service: Optional[GitHubReviewService] = None,
        analysis_engine: Optional[AnalysisEngine] = None,
        risk_scorer: Optional[PRRiskScorer] = None,
        inline_mapper: Optional[InlineCommentMapper] = None,
        comment_builder: Optional[PRCommentBuilder] = None,
        portal_url: Optional[str] = None,
        db_session=None,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        auth = get_auth_provider()
        client = GitHubClient(auth_provider=auth)

        self.pr_service = pr_service or GitHubPullRequestService(client)
        self.review_service = review_service or GitHubReviewService(client)
        self.engine = analysis_engine or AnalysisEngine(LeakGuardConfig())
        self.risk_scorer = risk_scorer or PRRiskScorer()
        self.inline_mapper = inline_mapper or InlineCommentMapper()
        portal = portal_url or os.getenv("LEAKGUARD_PORTAL_URL", "http://localhost:3000")
        self.comment_builder = comment_builder or PRCommentBuilder(portal_url=portal)
        self.redactor = SecretRedactor()
        if db_session is None:
            try:
                from packages.saas.db.database import _SessionLocal
                self.db = _SessionLocal()
            except Exception:
                self.db = None
        else:
            self.db = db_session
        self.org_id = org_id or "org_default"
        self.user_id = user_id or "system"

    def execute_pr_review(self, repo_full_name: str, pr_number: int, force: bool = True) -> Dict[str, Any]:
        """Trigger end-to-end PR review via GitHub API for a specified repo and PR number."""
        parts = repo_full_name.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid repository '{repo_full_name}'. Must be in 'owner/repo' format.")

        owner, repo_name = parts
        pr_obj = self.pr_service.get_pull_request(owner, repo_name, pr_number)

        event = PullRequestWebhookEvent(
            action="opened",
            pr_number=pr_number,
            head_sha=getattr(pr_obj, "head_sha", ""),
            base_sha=getattr(pr_obj, "base_sha", ""),
            head_branch=getattr(pr_obj, "head_branch", "main"),
            base_branch=getattr(pr_obj, "base_branch", "main"),
            repo_owner=owner,
            repo_name=repo_name,
            repo_full_name=repo_full_name,
            pr_title=getattr(pr_obj, "title", f"PR #{pr_number}"),
            pr_author=getattr(pr_obj, "author", "author"),
            pr_url=getattr(pr_obj, "url", f"https://github.com/{repo_full_name}/pull/{pr_number}"),
        )
        return self.process_webhook_event(event, force=force)

    def process_webhook_event(
        self, event: PullRequestWebhookEvent, force: bool = False
    ) -> Dict[str, Any]:
        """Process a pull_request webhook event end-to-end."""
        start_time = time.time()
        scan_id = str(uuid.uuid4())

        result: Dict[str, Any] = {
            "scan_id": scan_id,
            "pr_number": event.pr_number,
            "repo": event.repo_full_name,
            "head_sha": event.head_sha,
            "action": event.action,
            "status": "started",
            "findings": [],
            "risk": {},
            "pr_status": "UNKNOWN",
            "review_id": None,
            "summary_comment_id": None,
            "analysis_completed": False,
            "analysis_failed": False,
            "github_post_success": False,
            "github_post_error": None,
            "inline_comments_posted": 0,
            "error": None,
        }

        if self.db and (not self.org_id or self.org_id == "org_default"):
            try:
                from packages.saas.db.models import GithubRepository
                repo_rec = self.db.query(GithubRepository).filter(
                    GithubRepository.repo_full_name == event.repo_full_name
                ).first()
                if repo_rec:
                    self.org_id = repo_rec.org_id
            except Exception:
                pass

        try:
            self._audit("PR_SCAN_STARTED", "GithubPRScan", scan_id, {
                "pr_number": event.pr_number,
                "repo": event.repo_full_name,
                "head_sha": event.head_sha,
                "action": event.action,
            })

            if not force and self.db and self._is_duplicate_scan(
                event.repo_full_name, event.pr_number, event.head_sha
            ):
                result["status"] = "skipped_duplicate"
                result["error"] = "Duplicate scan for same repo+PR+sha"
                return result

            owner = event.repo_owner
            repo = event.repo_name
            pr_files = self.pr_service.get_python_files_only(owner, repo, event.pr_number)

            if not pr_files:
                result["status"] = "no_python_files"
                result["pr_status"] = "PASS"
                result["analysis_completed"] = True
                result["risk"] = self.risk_scorer.compute([])
                self._post_no_python_review(owner, repo, event.pr_number, event.head_sha)
                result["github_post_success"] = True
                return result

            all_diagnostics: List[Diagnostic] = []
            scanned_files: List[str] = []
            analysis_errors: List[str] = []

            for pr_file in pr_files:
                try:
                    content = self.pr_service.get_file_content(
                        owner, repo, pr_file.filename, event.head_sha
                    )
                    if not content.strip():
                        continue

                    redacted_text, _ = self.redactor.redact(content)
                    file_diagnostics = self.engine.analyze_code(
                        redacted_text, filename=pr_file.filename
                    )
                    all_diagnostics.extend(file_diagnostics)
                    scanned_files.append(pr_file.filename)
                    pr_file.content = content
                except Exception as exc:
                    analysis_errors.append(f"{pr_file.filename}: {exc}")

            if analysis_errors and not all_diagnostics and not scanned_files:
                result["status"] = "error"
                result["analysis_failed"] = True
                result["error"] = "; ".join(analysis_errors)
                return result

            result["analysis_completed"] = True

            risk = self.risk_scorer.compute(all_diagnostics)
            pr_status = self.risk_scorer.compute_pr_status(risk)
            result["risk"] = risk
            result["pr_status"] = pr_status

            changed_lines_map = self.inline_mapper.build_file_changed_lines_map(pr_files)
            inline_eligible, _summary_only = self.inline_mapper.filter_inline_eligible(
                all_diagnostics, changed_lines_map
            )

            ai_explanations = self._get_ai_explanations(all_diagnostics)
            ai_exp_list = list(ai_explanations.values())

            verified_fixes = self._count_verified_fixes(event.repo_full_name, event.pr_number)

            summary_body = self.comment_builder.build_summary_comment(
                pr_number=event.pr_number,
                repo_full_name=event.repo_full_name,
                risk=risk,
                pr_status=pr_status,
                diagnostics=all_diagnostics,
                ai_explanations=ai_exp_list,
                ai_available=bool(ai_explanations),
                pr_scan_id=scan_id,
                changed_files_count=len(scanned_files),
                verified_fixes_count=verified_fixes,
            )

            inline_comments: List[InlineComment] = []
            for diagnostic, line in inline_eligible:
                if diagnostic.classification == Classification.SAFE:
                    continue
                ai_exp = ai_explanations.get(diagnostic.finding_id)
                comment_body = self.comment_builder.build_inline_comment(
                    diagnostic, ai_exp, scan_id
                )
                inline_comments.append(
                    InlineComment(path=diagnostic.file_path, line=line, body=comment_body)
                )

            gh_event = "REQUEST_CHANGES" if pr_status == "FAIL" else "COMMENT"

            try:
                summary_result = self.review_service.upsert_summary_comment(
                    owner=owner,
                    repo=repo,
                    pr_number=event.pr_number,
                    body=summary_body,
                )
                result["summary_comment_id"] = summary_result.review_id
                result["github_post_success"] = True
            except GitHubAPIError as e:
                result["github_post_error"] = str(e)

            try:
                if inline_comments:
                    review_result = self.review_service.create_review(
                        owner=owner,
                        repo=repo,
                        pr_number=event.pr_number,
                        body="🛡️ LeakGuard inline findings — see summary comment above.",
                        event=gh_event,
                        comments=inline_comments,
                        commit_id=event.head_sha,
                    )
                    result["review_id"] = review_result.review_id
                    result["inline_comments_posted"] = len(inline_comments)
                    result["github_post_success"] = True
                elif not result["github_post_success"]:
                    review_result = self.review_service.create_review(
                        owner=owner,
                        repo=repo,
                        pr_number=event.pr_number,
                        body=summary_body,
                        event=gh_event,
                        commit_id=event.head_sha,
                    )
                    result["review_id"] = review_result.review_id
                    result["github_post_success"] = True
            except GitHubAPIError as e:
                if not result["github_post_success"]:
                    try:
                        fallback = self.review_service.create_issue_comment(
                            owner, repo, event.pr_number, summary_body
                        )
                        result["review_id"] = fallback.review_id
                        result["github_post_success"] = True
                    except Exception as fallback_err:
                        result["github_post_error"] = f"{e}; fallback: {fallback_err}"

            resolved_findings = self._detect_manual_fixes(
                event.repo_full_name, event.pr_number, all_diagnostics
            )

            if self.db:
                self._persist_scan(
                    scan_id=scan_id,
                    event=event,
                    diagnostics=all_diagnostics,
                    risk=risk,
                    pr_status=pr_status,
                    scanned_files=scanned_files,
                    review_id=result.get("review_id"),
                    ai_explanations=ai_explanations,
                    inline_comments=inline_comments,
                    resolved_findings=resolved_findings,
                )

            duration = time.time() - start_time
            result["status"] = "completed"
            result["findings"] = [
                self._serialize_diagnostic(d, ai_explanations.get(d.finding_id))
                for d in all_diagnostics
            ]
            result["scanned_files"] = scanned_files
            result["duration_seconds"] = round(duration, 2)
            result["resolved_findings"] = resolved_findings

            self._audit("PR_SCAN_COMPLETED", "GithubPRScan", scan_id, {
                "pr_status": pr_status,
                "risk_score": risk["score"],
                "findings_count": len(all_diagnostics),
                "analysis_completed": True,
                "github_post_success": result["github_post_success"],
                "duration_seconds": result["duration_seconds"],
            })

        except Exception as e:
            result["status"] = "error"
            result["analysis_failed"] = True
            result["error"] = str(e)
            self._audit("PR_SCAN_FAILED", "GithubPRScan", scan_id, {"error": str(e)})

        return result

    def _get_ai_explanations(
        self, diagnostics: List[Diagnostic]
    ) -> Dict[str, Dict[str, Any]]:
        """Get AI explanations for findings. Gracefully returns empty dict on failure."""
        try:
            from services.ai.agents.pr_review_agent import PRReviewAgent
            from services.ai.providers import get_llm_provider
            from services.ai.tracing import LangFuseTracer

            provider = get_llm_provider()
            tracer = LangFuseTracer(user_id=self.user_id, org_id=self.org_id)
            agent = PRReviewAgent(provider=provider, tracer=tracer)

            explanations: Dict[str, Dict[str, Any]] = {}
            for d in diagnostics:
                if d.classification not in (
                    Classification.DEFINITE_LEAK,
                    Classification.POTENTIAL_LEAK,
                ):
                    continue
                try:
                    agent_result = agent.run({
                        "finding_id": d.finding_id,
                        "classification": d.classification.value,
                        "rule_id": d.rule_id,
                        "file_path": d.file_path,
                        "line_number": d.location.start.line if d.location and d.location.start else 0,
                        "resource_type": str(d.resource_type),
                        "resource_variable": d.resource_variable,
                        "message": d.message,
                        "reason": d.reason or "",
                    })
                    exp = self._parse_ai_details(agent_result)
                    explanations[d.finding_id] = exp
                    self._audit("AI_REVIEW_REQUESTED", "GithubFinding", d.finding_id, {
                        "finding_id": d.finding_id,
                    })
                except Exception:
                    pass
            return explanations
        except Exception:
            return {}

    @staticmethod
    def _parse_ai_details(agent_result) -> Dict[str, Any]:
        """Parse AgentResult.details (JSON string or dict) into explanation dict."""
        if not hasattr(agent_result, "details") or not agent_result.details:
            return {}
        details = agent_result.details
        if isinstance(details, str):
            try:
                return json.loads(details)
            except json.JSONDecodeError:
                return {"summary": details}
        if isinstance(details, dict):
            return details
        return {}

    def _is_duplicate_scan(
        self, repo_full_name: str, pr_number: int, head_sha: str
    ) -> bool:
        if not self.db:
            return False
        try:
            from packages.saas.db.models import GithubPRScan
            existing = (
                self.db.query(GithubPRScan)
                .filter(
                    GithubPRScan.repo_full_name == repo_full_name,
                    GithubPRScan.pr_number == pr_number,
                    GithubPRScan.head_sha == head_sha,
                    GithubPRScan.status.in_(["completed", "started"]),
                )
                .first()
            )
            return existing is not None
        except Exception:
            return False

    def _detect_manual_fixes(
        self,
        repo_full_name: str,
        pr_number: int,
        current_diagnostics: List[Diagnostic],
    ) -> List[Dict[str, str]]:
        """Detect findings resolved by manual commits since last scan."""
        if not self.db:
            return []
        try:
            from packages.saas.db.models import GithubPRScan, GithubFinding

            prev_scan = (
                self.db.query(GithubPRScan)
                .filter(
                    GithubPRScan.repo_full_name == repo_full_name,
                    GithubPRScan.pr_number == pr_number,
                    GithubPRScan.status == "completed",
                )
                .order_by(GithubPRScan.created_at.desc())
                .offset(1)
                .first()
            )
            if not prev_scan:
                return []

            prev_findings = (
                self.db.query(GithubFinding)
                .filter(GithubFinding.pr_scan_id == prev_scan.id)
                .all()
            )
            current_ids = {d.finding_id for d in current_diagnostics}
            resolved = []
            for pf in prev_findings:
                if pf.finding_id not in current_ids:
                    resolved.append({
                        "finding_id": pf.finding_id,
                        "file_path": pf.file_path,
                        "resolved_by": "manual_fix",
                        "previous_scan_sha": prev_scan.head_sha,
                    })
                    self._audit("MANUAL_FIX_DETECTED", "GithubFinding", pf.finding_id, {
                        "finding_id": pf.finding_id,
                        "previous_scan": prev_scan.id,
                    })
            return resolved
        except Exception:
            return []

    def _count_verified_fixes(self, repo_full_name: str, pr_number: int) -> int:
        if not self.db:
            return 0
        try:
            from packages.saas.db.models import GithubPRScan, AIFixCandidate, GithubFinding
            scans = (
                self.db.query(GithubPRScan)
                .filter(
                    GithubPRScan.repo_full_name == repo_full_name,
                    GithubPRScan.pr_number == pr_number,
                )
                .all()
            )
            scan_ids = [s.id for s in scans]
            if not scan_ids:
                return 0
            findings = (
                self.db.query(GithubFinding)
                .filter(GithubFinding.pr_scan_id.in_(scan_ids))
                .all()
            )
            finding_ids = [f.id for f in findings]
            if not finding_ids:
                return 0
            return (
                self.db.query(AIFixCandidate)
                .filter(
                    AIFixCandidate.github_finding_id.in_(finding_ids),
                    AIFixCandidate.is_verified == True,  # noqa: E712
                )
                .count()
            )
        except Exception:
            return 0

    def _persist_scan(
        self,
        scan_id: str,
        event: PullRequestWebhookEvent,
        diagnostics: List[Diagnostic],
        risk: dict,
        pr_status: str,
        scanned_files: List[str],
        review_id: Optional[int],
        ai_explanations: Optional[Dict[str, Dict[str, Any]]] = None,
        inline_comments: Optional[List[InlineComment]] = None,
        resolved_findings: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        if not self.db:
            return
        try:
            from packages.saas.db.models import (
                GithubPRScan, GithubFinding, GithubReview, GithubReviewComment
            )

            scan = GithubPRScan(
                id=scan_id,
                org_id=self.org_id,
                repo_full_name=event.repo_full_name,
                pr_number=event.pr_number,
                head_sha=event.head_sha,
                base_sha=event.base_sha,
                pr_branch=event.head_branch,
                pr_author=event.pr_author,
                pr_title=event.pr_title,
                status="completed",
                risk_score=risk["score"],
                risk_label=risk["label"],
                pr_status=pr_status,
                definite_count=risk["definite_count"],
                potential_count=risk["potential_count"],
                safe_count=risk["safe_count"],
                scanned_files_json=json.dumps(scanned_files),
                github_review_id=str(review_id) if review_id else None,
            )
            self.db.merge(scan)

            ai_explanations = ai_explanations or {}
            resolved_ids = {r["finding_id"] for r in (resolved_findings or [])}

            for d in diagnostics:
                ai_exp = ai_explanations.get(d.finding_id, {})
                finding = GithubFinding(
                    id=str(uuid.uuid4()),
                    org_id=self.org_id,
                    pr_scan_id=scan_id,
                    finding_id=d.finding_id,
                    rule_id=d.rule_id,
                    file_path=d.file_path,
                    line_number=d.location.start.line if d.location and d.location.start else 0,
                    classification=d.classification.value,
                    resource_type=str(d.resource_type),
                    resource_variable=d.resource_variable,
                    message=d.message,
                    reason=d.reason or "",
                    ai_explanation_json=json.dumps(ai_exp) if ai_exp else None,
                )
                self.db.add(finding)
                self._audit("FINDING_CREATED", "GithubFinding", d.finding_id, {
                    "classification": d.classification.value,
                    "file": d.file_path,
                })

            for resolved in (resolved_findings or []):
                self._audit("MANUAL_FIX_DETECTED", "GithubFinding", resolved["finding_id"], resolved)

            review_db_id = None
            if review_id:
                review = GithubReview(
                    id=str(uuid.uuid4()),
                    org_id=self.org_id,
                    pr_scan_id=scan_id,
                    github_review_id=str(review_id),
                    status=pr_status,
                    risk_score=risk["score"],
                    finding_count=risk["definite_count"] + risk["potential_count"],
                )
                self.db.add(review)
                self.db.flush()
                review_db_id = review.id

            if review_db_id and inline_comments:
                for ic in inline_comments:
                    self.db.add(GithubReviewComment(
                        id=str(uuid.uuid4()),
                        org_id=self.org_id,
                        review_id=review_db_id,
                        file_path=ic.path,
                        line_number=ic.line,
                        body=ic.body,
                    ))

            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def _audit(
        self, action: str, resource_type: str, resource_id: str, details: dict
    ) -> None:
        if not self.db:
            return
        try:
            from packages.saas.middleware.audit import log_audit_event
            log_audit_event(
                self.db,
                org_id=self.org_id,
                user_id=self.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            pass

    def _post_no_python_review(
        self, owner: str, repo: str, pr_number: int, commit_id: str
    ) -> None:
        try:
            body = (
                "<!-- leakguard-review -->\n"
                "## 🛡️ LeakGuard Code Review\n\n"
                "✅ No Python files changed in this pull request. "
                "LeakGuard static analysis skipped."
            )
            self.review_service.upsert_summary_comment(owner, repo, pr_number, body)
        except Exception:
            pass

    @staticmethod
    def _serialize_diagnostic(
        d: Diagnostic, ai_explanation: Optional[Dict[str, Any]] = None
    ) -> dict:
        return {
            "finding_id": d.finding_id,
            "rule_id": d.rule_id,
            "file_path": d.file_path,
            "line_number": d.location.start.line if d.location and d.location.start else 0,
            "line": d.location.start.line if d.location and d.location.start else 0,
            "classification": d.classification.value,
            "resource_type": str(d.resource_type),
            "resource_variable": d.resource_variable,
            "message": d.message,
            "reason": d.reason or "",
            "ai_explanation": ai_explanation or {},
        }
