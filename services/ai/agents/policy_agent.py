import time
from typing import Dict, Any, List
from core.common.models import Diagnostic, Classification
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


class PolicyAgent(BaseAgent):
    """AGENT 10 — POLICY AGENT
    
    Integrates with organization policy definitions to determine overall pass/fail status
    and enforce re-analysis rules without overriding deterministic findings.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Policy Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostics: List[Diagnostic] = context.get("diagnostics", [])
        policy_config: Dict[str, Any] = context.get("policy", {"fail_on_leak": True})

        blocking = [
            d for d in diagnostics
            if d.classification in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)
        ]

        fail_on_leak = policy_config.get("fail_on_leak", True)
        passed = len(blocking) == 0 if fail_on_leak else True

        duration = (time.perf_counter() - start) * 1000.0

        status_str = "POLICY PASSED" if passed else "POLICY FAILED"
        details = (
            f"Policy evaluation completed. Total findings: {len(diagnostics)}, "
            f"Blocking leaks: {len(blocking)}. Policy status: {status_str}."
        )

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED if passed else AgentStatus.FAILED,
            summary=status_str,
            details=details,
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(
            self.agent_name,
            AgentStatus.COMPLETED if passed else AgentStatus.FAILED,
            duration,
            res.summary,
        )
        return res
