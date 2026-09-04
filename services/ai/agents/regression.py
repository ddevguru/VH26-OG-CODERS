import time
from typing import Dict, Any, Optional
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus, FixCandidate


class RegressionAgent(BaseAgent):
    """AGENT 6 — REGRESSION AGENT
    
    Analyzes candidate patches for potential behavioral regressions (return values,
    double-close, exception safety, async context managers, release ordering).
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Regression Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        fix_candidate_data = context.get("fix_candidate")

        if not fix_candidate_data:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.SKIPPED,
                summary="No fix candidate provided — regression analysis skipped.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.SKIPPED, duration, res.summary)
            return res

        candidate_patch = fix_candidate_data.get("candidate_patch", "")
        diff = fix_candidate_data.get("unified_diff", "")

        prompt = (
            f"REGRESSION_ANALYSIS\n"
            f"Candidate Patch Diff:\n{diff}\n\n"
            f"Check for:\n"
            f"1. Return statement integrity\n"
            f"2. Exception propagation safety\n"
            f"3. Potential double-close risks\n"
            f"4. Release ordering semantics\n\n"
            f"Summarize regression risk (LOW, MEDIUM, HIGH)."
        )

        response, duration = self._execute_prompt(prompt, system_prompt="You are a code regression analysis agent.")

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            summary="Completed regression inspection on candidate patch.",
            details=response,
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
