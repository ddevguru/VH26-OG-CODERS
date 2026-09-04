import time
from typing import Dict, Any, Optional
from core.common.models import Diagnostic
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


class SecurityImpactAgent(BaseAgent):
    """AGENT 4 — SECURITY IMPACT AGENT
    
    Explains potential reliability and security risks of unclosed resources using
    conservative, non-exaggerated security terms ("may contribute to", "could result in").
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Security Impact Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")

        if not diagnostic:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.COMPLETED,
                summary="No security impact — code is resource safe.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
            return res

        res_type = str(diagnostic.resource_type).upper()
        var_name = diagnostic.resource_variable or "handle"

        # Pre-canned conservative impact assessments based on resource category
        impact_map = {
            "DATABASE": (
                f"Unreleased database connection '{var_name}' may contribute to connection-pool "
                "exhaustion, query latency spikes, and potential service degradation under load."
            ),
            "FILE": (
                f"Unclosed file descriptor '{var_name}' could result in process file-descriptor exhaustion "
                "(EMFILE/ENFILE errors), preventing subsequent file or socket open operations."
            ),
            "SOCKET": (
                f"Unreleased socket connection '{var_name}' may cause socket descriptor accumulation, "
                "ephemeral port exhaustion, and orphaned network connections."
            ),
            "HTTP": (
                f"Unclosed HTTP client session '{var_name}' may lead to connection pool saturation, "
                "socket leaks, and unhandled TCP state retention."
            ),
            "LOCK": (
                f"Unreleased concurrency lock '{var_name}' could cause thread or process deadlock "
                "and severe application blocking along exceptional exit branches."
            ),
            "SUBPROCESS": (
                f"Unterminated subprocess handle '{var_name}' may result in zombie process creation "
                "and system resource leaks."
            ),
        }

        default_impact = (
            f"Unclosed resource '{var_name}' of type '{diagnostic.resource_type}' may result in process "
            "handle exhaustion and cumulative resource leaks over time."
        )

        impact_desc = impact_map.get(res_type, default_impact)

        prompt = (
            f"SECURITY_IMPACT_ANALYSIS\n"
            f"Resource Type: {diagnostic.resource_type}\n"
            f"Variable: {var_name}\n"
            f"Classification: {diagnostic.classification.value}\n\n"
            f"Refine the conservative security impact explanation:"
        )

        response, duration = self._execute_prompt(prompt, system_prompt="You are a conservative application security assessment agent.")
        if not response or "[Ollama Error" in response or "[OpenAI" in response:
            response = impact_desc

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=diagnostic.finding_id,
            summary=impact_desc,
            details=response,
            recommendations=["Remediate using a context manager to eliminate resource exhaustion risks."],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
