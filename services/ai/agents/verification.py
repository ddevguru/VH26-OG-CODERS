import time
from typing import Dict, Any, Optional
from core.common.models import Diagnostic, Classification
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus, VerificationResult
from services.ai.validator import PatchValidator


class VerificationAgent(BaseAgent):
    """AGENT 7 — VERIFICATION AGENT (AUTHORITATIVE DETERMINISTIC VERIFIER)
    
    CRITICAL RULE: AI-generated fixes MUST NEVER be trusted automatically.
    
    Workflow:
    AI Candidate Patch
       ↓
    Apply patch in isolated temporary workspace
       ↓
    Run LeakGuard deterministic analyzer
       ↓
    Compare before/after findings
       ↓
    If leak cleared & no new leaks -> VERIFIED_FIX
    Else -> REJECTED
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Verification Agent", provider=provider, tracer=tracer)
        self.validator = PatchValidator()

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")
        fix_candidate: Optional[Dict[str, Any]] = context.get("fix_candidate")
        file_name: str = context.get("file_name", "target_module.py")

        if not diagnostic or not fix_candidate:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.SKIPPED,
                summary="Missing diagnostic or fix candidate — verification skipped.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.SKIPPED, duration, res.summary)
            return res

        orig_code = fix_candidate.get("original_code", "")
        cand_code = fix_candidate.get("candidate_patch", "")

        # Execute 9-step isolated deterministic patch validation
        report = self.validator.validate_patch(
            original_source=orig_code,
            candidate_source=cand_code,
            target_diagnostic=diagnostic,
            file_name=file_name,
        )

        duration = (time.perf_counter() - start) * 1000.0

        if report.is_valid:
            v_status = "VERIFIED_FIX"
            is_ver = True
            after_class = Classification.SAFE
            reason = "✓ Deterministic re-analysis verified target leak cleared with zero introduced leaks."
            summary = "✓ PATCH VERIFIED — Deterministic static analysis confirmed resource safety."
        else:
            v_status = "REJECTED"
            is_ver = False
            after_class = diagnostic.classification
            reason = f"❌ REJECTED: {report.failure_reason}"
            summary = f"❌ PATCH REJECTED — {report.failure_reason}"

        v_result = VerificationResult(
            finding_id=diagnostic.finding_id,
            status=v_status,
            is_verified=is_ver,
            before_classification=diagnostic.classification,
            after_classification=after_class,
            original_finding_cleared=report.original_finding_cleared,
            new_findings_introduced=report.new_findings_count,
            unified_diff=report.unified_diff,
            reason=reason,
            verification_steps=report.validation_steps,
        )

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED if is_ver else AgentStatus.FAILED,
            finding_id=diagnostic.finding_id,
            summary=summary,
            details=reason,
            evidence=[v_result.model_dump()],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(
            self.agent_name,
            AgentStatus.COMPLETED if is_ver else AgentStatus.FAILED,
            duration,
            res.summary,
        )
        return res
