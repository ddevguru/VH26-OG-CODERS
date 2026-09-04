import time
from typing import Dict, Any, Optional
from core.common.models import Diagnostic
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


class DocumentationAgent(BaseAgent):
    """AGENT 9 — DOCUMENTATION AGENT
    
    Generates optional developer documentation for verified fixes explaining
    what was wrong, why it happened, and recommended safe coding patterns.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Documentation Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")

        if not diagnostic:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.SKIPPED,
                summary="No diagnostic — documentation generation skipped.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.SKIPPED, duration, res.summary)
            return res

        var_name = diagnostic.resource_variable or "resource"
        prompt = (
            f"DOCUMENTATION_GENERATOR\n"
            f"Resource: {var_name} ({diagnostic.resource_type})\n"
            f"Rule: {diagnostic.rule_id}\n\n"
            f"Generate a brief developer remediation guide explaining:\n"
            f"1. What was wrong\n2. Why it happened\n3. Recommended context manager pattern"
        )

        response, duration = self._execute_prompt(prompt, system_prompt="You are a developer documentation generator.")

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=diagnostic.finding_id,
            summary=f"Generated remediation documentation for {var_name}",
            details=response,
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
