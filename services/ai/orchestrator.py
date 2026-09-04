import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from core.common.models import Diagnostic, Classification
from services.ai.models import (
    ReviewResult,
    AgentResult,
    FixCandidate,
    VerificationResult,
    ReviewMode,
    AgentStatus,
)
from services.ai.providers import LLMProvider, get_llm_provider
from services.ai.tracing import LangFuseTracer

# Import specialized agents
from services.ai.agents.resource_hunter import ResourceHunterAgent
from services.ai.agents.code_reviewer import CodeReviewerAgent
from services.ai.agents.root_cause import RootCauseAgent
from services.ai.agents.security_impact import SecurityImpactAgent
from services.ai.agents.fix_generator import FixGeneratorAgent
from services.ai.agents.regression import RegressionAgent
from services.ai.agents.verification import VerificationAgent
from services.ai.agents.pr_agent import PRAgent
from services.ai.agents.documentation import DocumentationAgent
from services.ai.agents.policy_agent import PolicyAgent


class AIOrchestrator:
    """Central AI Multi-Agent Orchestrator for LeakGuard.
    
    Coordinates specialized agents for AI Code Review, Root-Cause Analysis,
    Security Risk Explanation, Fix Generation, and Isolated Deterministic Verification.
    
    Tied to LangFuseTracer for tenant (org_id) and user (user_id) execution logging.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.user_id = user_id or "user_default"
        self.org_id = org_id or "org_default"
        self.tracer = LangFuseTracer(user_id=self.user_id, org_id=self.org_id)

        # Initialize specialized agents with shared provider and tracer
        self.hunter_agent = ResourceHunterAgent(provider=self.provider, tracer=self.tracer)
        self.reviewer_agent = CodeReviewerAgent(provider=self.provider, tracer=self.tracer)
        self.root_cause_agent = RootCauseAgent(provider=self.provider, tracer=self.tracer)
        self.security_agent = SecurityImpactAgent(provider=self.provider, tracer=self.tracer)
        self.fix_agent = FixGeneratorAgent(provider=self.provider, tracer=self.tracer)
        self.regression_agent = RegressionAgent(provider=self.provider, tracer=self.tracer)
        self.verifier_agent = VerificationAgent(provider=self.provider, tracer=self.tracer)
        self.pr_agent = PRAgent(provider=self.provider, tracer=self.tracer)
        self.doc_agent = DocumentationAgent(provider=self.provider, tracer=self.tracer)
        self.policy_agent = PolicyAgent(provider=self.provider, tracer=self.tracer)

    def review(
        self,
        diagnostics: List[Diagnostic],
        source_code: str = "",
        review_mode: ReviewMode = ReviewMode.DETAILED,
        target_name: str = "Project",
    ) -> ReviewResult:
        """Executes full multi-agent resource security review on findings."""
        trace_id = self.tracer.start_trace("Resource Safety Review")
        agent_results: List[AgentResult] = []

        # 1. Policy Agent check
        policy_res = self.policy_agent.run({"diagnostics": diagnostics})
        agent_results.append(policy_res)

        # 2. Code Reviewer Agent
        review_res = self.reviewer_agent.run({
            "diagnostics": diagnostics,
            "source_code": source_code,
            "review_mode": review_mode,
            "target_name": target_name,
        })
        agent_results.append(review_res)

        # 3. For each active finding, run Hunter, Root Cause, & Security agents
        explanations = []
        for diag in diagnostics:
            hunter_res = self.hunter_agent.run({"diagnostic": diag, "source_code": source_code})
            rc_res = self.root_cause_agent.run({"diagnostic": diag, "source_code": source_code})
            sec_res = self.security_agent.run({"diagnostic": diag})

            agent_results.extend([hunter_res, rc_res, sec_res])
            explanations.append({
                "finding_id": diag.finding_id,
                "rule_id": diag.rule_id,
                "classification": diag.classification.value,
                "hunter_summary": hunter_res.summary,
                "root_cause": rc_res.details,
                "security_impact": sec_res.summary,
            })

        new_leaks = len([d for d in diagnostics if d.classification != Classification.SAFE])
        overall = "FAILED" if new_leaks > 0 else "PASSED"

        return ReviewResult(
            target=target_name,
            review_mode=review_mode,
            total_files_reviewed=1,
            new_leaks_count=new_leaks,
            resolved_leaks_count=0,
            overall_status=overall,
            summary=review_res.details,
            findings_explanations=explanations,
            agent_results=agent_results,
            activity_timeline=list(self.tracer.logs),
            user_id=self.user_id,
            org_id=self.org_id,
            trace_id=trace_id,
        )

    def explain(self, diagnostic: Diagnostic, source_code: str = "") -> Dict[str, Any]:
        """Provides full multi-agent explanation for a single finding."""
        trace_id = self.tracer.start_trace(f"Explain Finding {diagnostic.finding_id}")

        hunter_res = self.hunter_agent.run({"diagnostic": diagnostic, "source_code": source_code})
        rc_res = self.root_cause_agent.run({"diagnostic": diagnostic, "source_code": source_code})
        sec_res = self.security_agent.run({"diagnostic": diagnostic})

        return {
            "finding_id": diagnostic.finding_id,
            "resource_variable": diagnostic.resource_variable,
            "resource_type": diagnostic.resource_type,
            "classification": diagnostic.classification.value,
            "summary": hunter_res.summary,
            "root_cause": rc_res.details,
            "security_impact": sec_res.summary,
            "evidence": rc_res.evidence,
            "trace_id": trace_id,
            "timeline": list(self.tracer.logs),
        }

    def generate_and_verify_fix(
        self,
        diagnostic: Diagnostic,
        source_code: str,
        file_name: str = "target_module.py",
    ) -> Dict[str, Any]:
        """Full automated Fix Generation & Deterministic Verification pipeline.
        
        Fix Generator -> Candidate Patch -> Regression Inspection -> Verification Agent
        -> Deterministic LeakGuard Re-analysis -> VERIFIED_FIX or REJECTED
        """
        trace_id = self.tracer.start_trace(f"Fix & Verify {diagnostic.finding_id}")

        # Step 1: Fix Generator Agent
        fix_res = self.fix_agent.run({
            "diagnostic": diagnostic,
            "source_code": source_code,
            "file_name": file_name,
        })

        if fix_res.status == AgentStatus.SKIPPED or not fix_res.evidence:
            return {
                "status": "REJECTED",
                "reason": "Failed to generate candidate patch.",
                "trace_id": trace_id,
                "timeline": list(self.tracer.logs),
            }

        fix_candidate = fix_res.evidence[0]

        # Step 2: Regression Agent Inspection
        reg_res = self.regression_agent.run({"fix_candidate": fix_candidate})

        # Step 3: Verification Agent (Authoritative Isolated Deterministic Re-analysis)
        ver_res = self.verifier_agent.run({
            "diagnostic": diagnostic,
            "fix_candidate": fix_candidate,
            "file_name": file_name,
        })

        # Step 4: Documentation Agent (if verified)
        doc_res = None
        if ver_res.status == AgentStatus.COMPLETED:
            doc_res = self.doc_agent.run({"diagnostic": diagnostic})

        verification_details = ver_res.evidence[0] if ver_res.evidence else {}

        return {
            "finding_id": diagnostic.finding_id,
            "candidate_patch": fix_candidate.get("candidate_patch", ""),
            "unified_diff": fix_candidate.get("unified_diff", ""),
            "verification_status": verification_details.get("status", "REJECTED"),
            "is_verified": verification_details.get("is_verified", False),
            "reason": verification_details.get("reason", ""),
            "verification_steps": verification_details.get("verification_steps", []),
            "documentation": doc_res.details if doc_res else "",
            "trace_id": trace_id,
            "timeline": list(self.tracer.logs),
        }

    def review_pull_request(
        self,
        diagnostics: List[Diagnostic],
        files_count: int = 1,
        pr_number: str = "PR #1",
        resolved_count: int = 0,
        verified_fixes_count: int = 0,
    ) -> ReviewResult:
        """PR Agent & Multi-Agent Pull Request Review pipeline."""
        trace_id = self.tracer.start_trace(f"PR Review {pr_number}")

        new_leaks = len([d for d in diagnostics if d.classification != Classification.SAFE])

        pr_res = self.pr_agent.run({
            "files_count": files_count,
            "new_leaks": new_leaks,
            "resolved_leaks": resolved_count,
            "verified_fixes": verified_fixes_count,
            "pr_number": pr_number,
        })

        overall = "PASSED" if new_leaks == 0 else "FAILED"

        return ReviewResult(
            target=pr_number,
            review_mode=ReviewMode.DETAILED,
            total_files_reviewed=files_count,
            new_leaks_count=new_leaks,
            resolved_leaks_count=resolved_count,
            overall_status=overall,
            summary=pr_res.details,
            agent_results=[pr_res],
            activity_timeline=list(self.tracer.logs),
            user_id=self.user_id,
            org_id=self.org_id,
            trace_id=trace_id,
        )
