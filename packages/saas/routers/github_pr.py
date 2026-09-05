"""GitHub PR Review API Router — portal endpoints for PR scanning and fix workflow."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import (
    GithubRepository, GithubPRScan, GithubFinding,
    GithubReview, AIFixCandidate, PatchVerification,
    RoleEnum, AuditEvent,
)
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.middleware.audit import log_audit_event
from packages.saas.config import settings

router = APIRouter(prefix="/github", tags=["GitHub PR Review"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def github_pr_webhook_alias(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
):
    from packages.saas.routers.webhooks import github_webhook
    return await github_webhook(request, background_tasks, x_hub_signature_256, x_github_event, x_github_delivery)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ConnectRepoRequest(BaseModel):
    repo_full_name: str = Field(..., description="GitHub repo in owner/repo format")
    github_token: Optional[str] = Field(None, description="Override token (stored server-side only)")


class GenerateFixRequest(BaseModel):
    strategy: str = Field("try_finally", description="Fix strategy: try_finally, context_manager, explicit_close")
    source_code: Optional[str] = Field(None, description="Current source code (auto-fetched from GitHub if omitted)")


class CommitFixRequest(BaseModel):
    fix_candidate_id: str
    committer_name: Optional[str] = "LeakGuard Bot"
    committer_email: Optional[str] = "leakguard-bot@noreply.leakguard.io"


# ─────────────────────────────────────────────────────────────────────────────
# Repository Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/repositories")
def list_repositories(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """List all GitHub repositories connected to this organization."""
    repos = db.query(GithubRepository).filter(
        GithubRepository.org_id == ctx.org_id,
        GithubRepository.is_active == True,
    ).all()
    return [
        {
            "id": r.id,
            "repo_full_name": r.repo_full_name,
            "repo_owner": r.repo_owner,
            "repo_name": r.repo_name,
            "default_branch": r.default_branch,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in repos
    ]


@router.post("/repositories/connect", status_code=status.HTTP_201_CREATED)
def connect_repository(
    req: ConnectRepoRequest,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    """Connect a GitHub repository to LeakGuard for PR review scanning."""
    # Validate repo format
    parts = req.repo_full_name.strip().split("/")
    if len(parts) != 2:
        raise HTTPException(400, "repo_full_name must be in 'owner/repo' format")

    owner, repo_name = parts

    # Check if already connected
    existing = db.query(GithubRepository).filter(
        GithubRepository.org_id == ctx.org_id,
        GithubRepository.repo_full_name == req.repo_full_name,
    ).first()
    if existing:
        existing.is_active = True
        db.commit()
        return {"id": existing.id, "status": "already_connected", "repo_full_name": req.repo_full_name}

    # Verify GitHub access
    try:
        from packages.github.client import GitHubClient
        from packages.github.auth import get_auth_provider
        client = GitHubClient(auth_provider=get_auth_provider())
        repo_data = client.get(f"/repos/{owner}/{repo_name}")
        default_branch = repo_data.get("default_branch", "main")
    except Exception as e:
        raise HTTPException(400, f"Cannot access GitHub repository: {e}")

    new_repo = GithubRepository(
        id=str(uuid.uuid4()),
        org_id=ctx.org_id,
        repo_full_name=req.repo_full_name,
        repo_owner=owner,
        repo_name=repo_name,
        default_branch=default_branch,
        is_active=True,
    )
    db.add(new_repo)
    db.commit()

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "PR_CONNECTED", "GithubRepository", new_repo.id,
                    {"repo": req.repo_full_name})

    from packages.saas.config import settings
    webhook_url = f"{getattr(settings, 'leakguard_portal_url', 'http://localhost:8000').replace('3000', '8000')}/webhooks/github"

    return {
        "id": new_repo.id,
        "status": "connected",
        "repo_full_name": req.repo_full_name,
        "webhook_url": webhook_url,
        "setup_instructions": (
            f"Configure GitHub webhook:\n"
            f"  URL: {webhook_url}\n"
            f"  Content-Type: application/json\n"
            f"  Secret: $GITHUB_WEBHOOK_SECRET\n"
            f"  Events: Pull requests"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pull Request Scans
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/prs")
def list_pull_requests(
    limit: int = 20,
    offset: int = 0,
    repo_full_name: Optional[str] = None,
    pr_number: Optional[int] = None,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """List PR scans for this organization and connected repositories."""
    org_repos = db.query(GithubRepository.repo_full_name).filter(
        GithubRepository.org_id == ctx.org_id
    ).all()
    org_repo_names = [r[0] for r in org_repos]

    from sqlalchemy import or_
    filters = [GithubPRScan.org_id == ctx.org_id, GithubPRScan.org_id == "org_default"]
    if org_repo_names:
        filters.append(GithubPRScan.repo_full_name.in_(org_repo_names))

    query = db.query(GithubPRScan).filter(or_(*filters))

    if repo_full_name:
        query = query.filter(GithubPRScan.repo_full_name == repo_full_name)
    if pr_number:
        query = query.filter(GithubPRScan.pr_number == pr_number)

    query = query.order_by(GithubPRScan.created_at.desc())

    total = query.count()
    scans = query.offset(offset).limit(limit).all()

    return {
        "items": [_serialize_pr_scan(s) for s in scans],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/prs/{pr_scan_id}")
def get_pull_request(
    pr_scan_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Get full details for a PR scan including findings and review."""
    scan = _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    findings = db.query(GithubFinding).filter(
        GithubFinding.pr_scan_id == pr_scan_id
    ).all()

    return {
        **_serialize_pr_scan(scan),
        "findings": [_serialize_finding(f) for f in findings],
    }


@router.get("/prs/{pr_scan_id}/findings")
def get_pr_findings(
    pr_scan_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Get all findings for a PR scan."""
    _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    findings = db.query(GithubFinding).filter(
        GithubFinding.pr_scan_id == pr_scan_id
    ).all()
    return [_serialize_finding(f) for f in findings]


@router.get("/prs/{pr_scan_id}/review")
def get_pr_review(
    pr_scan_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Get the GitHub review posted for a PR scan."""
    _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    review = db.query(GithubReview).filter(
        GithubReview.pr_scan_id == pr_scan_id,
        GithubReview.org_id == ctx.org_id,
    ).first()
    if not review:
        raise HTTPException(404, "No review found for this PR scan")
    return {
        "id": review.id,
        "github_review_id": review.github_review_id,
        "status": review.status,
        "risk_score": review.risk_score,
        "finding_count": review.finding_count,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Fix Workflow
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/prs/{pr_scan_id}/findings/{finding_db_id}/fix")
def generate_fix(
    pr_scan_id: str,
    finding_db_id: str,
    req: GenerateFixRequest,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    """Generate and verify an AI fix for a specific finding.

    Flow:
    1. AI generates candidate patch
    2. LeakGuard deterministic re-scan validates patch (isolated workspace)
    3. Result returned — NOT committed (user must explicitly commit)
    """
    scan = _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    finding = _get_finding_or_404(db, finding_db_id, ctx.org_id)

    source_code = req.source_code
    if not source_code:
        parts = scan.repo_full_name.split("/")
        if len(parts) == 2:
            owner, repo_name = parts
            try:
                from packages.github.client import GitHubClient
                from packages.github.auth import get_auth_provider
                from packages.github.services.pull_request import GitHubPullRequestService
                client = GitHubClient(auth_provider=get_auth_provider())
                pr_service = GitHubPullRequestService(client)
                source_code = pr_service.get_file_content(
                    owner, repo_name, finding.file_path, scan.head_sha
                )
            except Exception as e:
                raise HTTPException(400, f"Could not fetch source from GitHub: {e}. Provide source_code manually.")
        else:
            raise HTTPException(400, "source_code required when GitHub fetch unavailable")

    if not source_code or not source_code.strip():
        raise HTTPException(400, "source_code is required and cannot be empty")

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "AI_FIX_REQUESTED", "GithubFinding", finding_db_id,
                    {"strategy": req.strategy})

    # Run the existing AutoFixerEngine (unchanged)
    from core.common.models import Diagnostic, Classification, Span, SourceLocation
    from services.ai.auto_fixer import AutoFixerEngine
    from services.ai.validator import PatchValidator

    diag = Diagnostic(
        finding_id=finding.finding_id,
        rule_id=finding.rule_id,
        message=finding.message or "",
        classification=Classification(finding.classification),
        file_path=finding.file_path,
        location=Span(
            start=SourceLocation(line=finding.line_number, column=1),
            end=SourceLocation(line=finding.line_number, column=10),
        ),
        resource_type=finding.resource_type or "FILE",
        resource_variable=finding.resource_variable or "resource",
        reason=finding.reason or "",
    )

    fixer = AutoFixerEngine(validator=PatchValidator())
    patch_result = fixer.generate_and_verify(
        source_code=source_code,
        diagnostic=diag,
        strategy_name=req.strategy,
        file_name=finding.file_path,
    )

    # Persist fix candidate
    fix = AIFixCandidate(
        id=str(uuid.uuid4()),
        org_id=ctx.org_id,
        github_finding_id=finding_db_id,
        user_id=ctx.user.id if ctx.user else None,
        strategy=patch_result.strategy,
        candidate_code=patch_result.candidate_code,
        unified_diff=patch_result.unified_diff,
        explanation=patch_result.explanation,
        verification_status=patch_result.verification_status,
        is_verified=patch_result.is_verified,
        before_findings=patch_result.before_findings,
        after_findings=patch_result.after_findings,
        rejected_reason=patch_result.rejected_reason,
        verification_steps_json=json.dumps(patch_result.verification_steps),
    )
    db.add(fix)

    # Persist verification record
    verif = PatchVerification(
        id=str(uuid.uuid4()),
        org_id=ctx.org_id,
        fix_candidate_id=fix.id,
        is_valid=patch_result.is_verified,
        original_finding_cleared=patch_result.is_verified,
        new_findings_count=patch_result.after_findings,
        syntax_valid=True,
        failure_reason=patch_result.rejected_reason,
        unified_diff=patch_result.unified_diff,
        validation_steps_json=json.dumps(patch_result.verification_steps),
    )
    db.add(verif)
    db.commit()

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "PATCH_GENERATED" if patch_result.is_verified else "PATCH_REJECTED",
                    "AIFixCandidate", fix.id,
                    {"strategy": req.strategy, "verified": patch_result.is_verified})

    return {
        "fix_candidate_id": fix.id,
        "strategy": patch_result.strategy,
        "explanation": patch_result.explanation,
        "unified_diff": patch_result.unified_diff,
        "verification_status": patch_result.verification_status,
        "is_verified": patch_result.is_verified,
        "before_findings": patch_result.before_findings,
        "after_findings": patch_result.after_findings,
        "rejected_reason": patch_result.rejected_reason,
        "verification_steps": patch_result.verification_steps,
    }


@router.post("/prs/{pr_scan_id}/findings/{finding_db_id}/commit")
def commit_verified_fix(
    pr_scan_id: str,
    finding_db_id: str,
    req: CommitFixRequest,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    """Apply a verified fix by creating a commit on the PR branch.

    CRITICAL SECURITY RULES:
    - Only VERIFIED fixes can be committed (is_verified=True)
    - User must be authenticated and have DEVELOPER+ role
    - Commit is created on the PR source branch only
    - Never auto-committed — always requires explicit user action
    """
    scan = _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    finding = _get_finding_or_404(db, finding_db_id, ctx.org_id)

    # Get fix candidate
    fix = db.query(AIFixCandidate).filter(
        AIFixCandidate.id == req.fix_candidate_id,
        AIFixCandidate.github_finding_id == finding_db_id,
        AIFixCandidate.org_id == ctx.org_id,
    ).first()
    if not fix:
        raise HTTPException(404, "Fix candidate not found")

    # ENFORCE: only verified patches can be committed
    if not fix.is_verified:
        raise HTTPException(
            400,
            f"Cannot commit unverified patch. Verification status: {fix.verification_status}. "
            f"Reason: {fix.rejected_reason or 'Unknown'}"
        )

    if not fix.candidate_code:
        raise HTTPException(400, "Fix candidate has no code content")

    # Determine branch and file
    branch = scan.pr_branch
    if not branch:
        raise HTTPException(400, "PR branch not available for commit")

    repo_parts = scan.repo_full_name.split("/")
    if len(repo_parts) != 2:
        raise HTTPException(400, "Invalid repository name in scan record")
    owner, repo_name = repo_parts

    # Generate commit message
    from packages.github.services.commit import GitHubCommitService
    commit_service = GitHubCommitService()

    commit_message = commit_service.generate_commit_message(
        resource_type=finding.resource_type or "resource",
        finding_summary=finding.message or "",
        strategy=fix.strategy,
    )

    try:
        result = commit_service.create_or_update_file(
            owner=owner,
            repo=repo_name,
            branch=branch,
            file_path=finding.file_path,
            new_content=fix.candidate_code,
            commit_message=commit_message,
            committer_name=req.committer_name or "LeakGuard Bot",
            committer_email=req.committer_email or "leakguard-bot@noreply.leakguard.io",
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to create GitHub commit: {e}")

    commit_sha = result.get("commit", {}).get("sha", "")

    # Update fix record
    fix.commit_sha = commit_sha
    fix.committed_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "COMMIT_CREATED", "AIFixCandidate", fix.id,
                    {"commit_sha": commit_sha, "branch": branch, "file": finding.file_path})

    return {
        "status": "committed",
        "commit_sha": commit_sha,
        "branch": branch,
        "file_path": finding.file_path,
        "commit_message": commit_message,
        "message": (
            f"Fix committed to branch '{branch}'. "
            "GitHub will trigger a new PR webhook for re-scan."
        ),
    }


@router.post("/prs/{pr_scan_id}/findings/{finding_db_id}/reject-fix")
def reject_fix(
    pr_scan_id: str,
    finding_db_id: str,
    fix_candidate_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    """User explicitly rejects a fix candidate."""
    _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    fix = db.query(AIFixCandidate).filter(
        AIFixCandidate.id == fix_candidate_id,
        AIFixCandidate.org_id == ctx.org_id,
    ).first()
    if not fix:
        raise HTTPException(404, "Fix candidate not found")

    fix.verification_status = "REJECTED"
    db.commit()

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "PATCH_REJECTED", "AIFixCandidate", fix_candidate_id, {})
    return {"status": "rejected", "fix_candidate_id": fix_candidate_id}


@router.get("/prs/{pr_scan_id}/findings/{finding_db_id}/source")
def get_finding_source(
    pr_scan_id: str,
    finding_db_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Fetch current source code for a finding's file from GitHub."""
    scan = _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    finding = _get_finding_or_404(db, finding_db_id, ctx.org_id)

    parts = scan.repo_full_name.split("/")
    if len(parts) != 2:
        raise HTTPException(400, "Invalid repository name")
    owner, repo_name = parts

    try:
        from packages.github.client import GitHubClient
        from packages.github.auth import get_auth_provider
        from packages.github.services.pull_request import GitHubPullRequestService

        client = GitHubClient(auth_provider=get_auth_provider())
        pr_service = GitHubPullRequestService(client)
        content = pr_service.get_file_content(
            owner, repo_name, finding.file_path, scan.head_sha
        )
        return {
            "file_path": finding.file_path,
            "head_sha": scan.head_sha,
            "source_code": content,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch source from GitHub: {e}")


@router.post("/prs/{pr_scan_id}/findings/{finding_db_id}/explain")
def explain_finding(
    pr_scan_id: str,
    finding_db_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Generate on-demand AI root cause explanation for a finding."""
    _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    finding = _get_finding_or_404(db, finding_db_id, ctx.org_id)

    log_audit_event(db, ctx.org_id, ctx.user.id if ctx.user else None,
                    "AI_REVIEW_REQUESTED", "GithubFinding", finding_db_id, {})

    from services.ai.agents.pr_review_agent import PRReviewAgent
    from services.ai.providers import get_llm_provider
    from services.ai.tracing import LangFuseTracer
    from services.github_pr.orchestrator import PRReviewOrchestrator

    agent = PRReviewAgent(provider=get_llm_provider(), tracer=LangFuseTracer(
        user_id=ctx.user.id if ctx.user else "system", org_id=ctx.org_id
    ))
    result = agent.run({
        "finding_id": finding.finding_id,
        "classification": finding.classification,
        "rule_id": finding.rule_id,
        "file_path": finding.file_path,
        "line_number": finding.line_number,
        "resource_type": finding.resource_type or "FILE",
        "resource_variable": finding.resource_variable or "resource",
        "message": finding.message or "",
        "reason": finding.reason or "",
    })
    explanation = PRReviewOrchestrator._parse_ai_details(result)
    finding.ai_explanation_json = json.dumps(explanation)
    db.commit()

    return {"finding_id": finding.finding_id, "ai_explanation": explanation}


@router.get("/prs/{pr_scan_id}/audit")
def get_pr_audit_trail(
    pr_scan_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    """Get audit trail events for a PR scan."""
    scan = _get_scan_or_404(db, pr_scan_id, ctx.org_id)
    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.org_id == ctx.org_id,
            AuditEvent.resource_id.in_([pr_scan_id, scan.repo_full_name]),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
    pr_events = [
        e for e in events
        if e.action.startswith("PR_") or e.action.startswith("AI_")
        or e.action.startswith("PATCH_") or e.action.startswith("COMMIT_")
        or e.action.startswith("FINDING_") or e.action.startswith("MANUAL_")
    ]
    return [
        {
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "details": json.loads(e.details_json) if e.details_json else {},
            "timestamp": e.created_at.isoformat() if e.created_at else None,
        }
        for e in pr_events
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Trigger Manual PR Review
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/prs/trigger-review")
def trigger_manual_review(
    repo_full_name: str,
    pr_number: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """Manually trigger a PR review (equivalent to webhook, for testing/CI).

    Auth: X-Webhook-Secret header matching GITHUB_WEBHOOK_SECRET (for CI/webhooks).
    """
    ci_authorized = (
        settings.github_webhook_secret
        and x_webhook_secret
        and x_webhook_secret == settings.github_webhook_secret
    )

    if not ci_authorized:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required: provide X-Webhook-Secret header matching GITHUB_WEBHOOK_SECRET",
        )

    org_id = "org_default"
    repo_record = db.query(GithubRepository).filter(
        GithubRepository.repo_full_name == repo_full_name,
        GithubRepository.is_active == True,
    ).first()
    if repo_record:
        org_id = repo_record.org_id

    def _run():
        _db = _SessionLocal_helper()
        try:
            from packages.github.client import GitHubClient
            from packages.github.auth import get_auth_provider
            from packages.github.services.pull_request import GitHubPullRequestService
            from packages.github.services.webhook import PullRequestWebhookEvent
            from services.github_pr.orchestrator import PRReviewOrchestrator

            client = GitHubClient(auth_provider=get_auth_provider())
            pr_service = GitHubPullRequestService(client)
            parts = repo_full_name.split("/")
            if len(parts) != 2:
                return
            owner, repo = parts
            pr = pr_service.get_pull_request(owner, repo, pr_number)

            event = PullRequestWebhookEvent(
                action="opened",
                pr_number=pr_number,
                head_sha=pr.head_sha,
                base_sha=pr.base_sha,
                head_branch=pr.head_branch,
                base_branch=pr.base_branch,
                repo_owner=owner,
                repo_name=repo,
                repo_full_name=repo_full_name,
                pr_title=pr.title,
                pr_author=pr.author,
                pr_url=pr.url,
            )
            orch = PRReviewOrchestrator(db_session=_db, org_id=org_id)
            orch.process_webhook_event(event, force=True)
        finally:
            try:
                _db.close()
            except Exception:
                pass

    from packages.saas.db.database import _SessionLocal as _SessionLocal_helper
    background_tasks.add_task(_run)

    return {"status": "queued", "repo": repo_full_name, "pr_number": pr_number}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_scan_or_404(db, scan_id: str, org_id: str) -> GithubPRScan:
    scan = db.query(GithubPRScan).filter(
        GithubPRScan.id == scan_id,
        GithubPRScan.org_id == org_id,
    ).first()
    if not scan:
        raise HTTPException(404, "PR scan not found")
    return scan


def _get_finding_or_404(db, finding_id: str, org_id: str) -> GithubFinding:
    finding = db.query(GithubFinding).filter(
        GithubFinding.id == finding_id,
        GithubFinding.org_id == org_id,
    ).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    return finding


def _serialize_pr_scan(scan: GithubPRScan) -> dict:
    return {
        "id": scan.id,
        "repo_full_name": scan.repo_full_name,
        "pr_number": scan.pr_number,
        "head_sha": scan.head_sha,
        "pr_branch": scan.pr_branch,
        "pr_author": scan.pr_author,
        "pr_title": scan.pr_title,
        "status": scan.status,
        "risk_score": scan.risk_score,
        "risk_label": scan.risk_label,
        "pr_status": scan.pr_status,
        "definite_count": scan.definite_count,
        "potential_count": scan.potential_count,
        "safe_count": scan.safe_count,
        "scanned_files": json.loads(scan.scanned_files_json or "[]"),
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }


def _serialize_finding(f: GithubFinding) -> dict:
    ai_exp = {}
    if f.ai_explanation_json:
        try:
            ai_exp = json.loads(f.ai_explanation_json)
        except Exception:
            pass
    return {
        "id": f.id,
        "finding_id": f.finding_id,
        "rule_id": f.rule_id,
        "file_path": f.file_path,
        "line_number": f.line_number,
        "classification": f.classification,
        "resource_type": f.resource_type,
        "resource_variable": f.resource_variable,
        "message": f.message,
        "reason": f.reason,
        "ai_explanation": ai_exp,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }
