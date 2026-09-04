import time
from typing import Dict, Any, Optional
from core.common.models import Diagnostic
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


class RootCauseAgent(BaseAgent):
    """AGENT 3 — ROOT CAUSE AGENT
    
    Identifies acquisition location, owner function, exit path, missing lifecycle
    event, and underlying cause for why the deterministic analyzer classified a leak.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Root Cause Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")
        source_code: str = context.get("source_code", "")

        if not diagnostic:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.COMPLETED,
                summary="No root cause required — code is resource safe.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
            return res

        line = diagnostic.location.start.line if diagnostic.location else 1
        var_name = diagnostic.resource_variable or "resource"
        func_name = getattr(diagnostic, "function_name", None) or "function"

        prompt = (
            f"ROOT_CAUSE_ANALYSIS\n"
            f"Resource: {var_name} ({diagnostic.resource_type})\n"
            f"Acquired: {diagnostic.file_path}:{line}\n"
            f"Owner: {func_name}()\n"
            f"Classification: {diagnostic.classification.value}\n"
            f"Reason: {diagnostic.reason}\n\n"
            f"Code Snippet:\n{source_code}\n\n"
            f"Explain:\n"
            f"1. Acquisition\n2. Owner\n3. Problem\n4. Missing lifecycle event\n5. Affected path\n6. Root cause"
        )

        response, duration = self._execute_prompt(prompt, system_prompt="You are a root cause analysis agent for static analysis findings.")

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=diagnostic.finding_id,
            summary=f"Root Cause: Resource '{var_name}' acquired at line {line} is missing release call on function exit path.",
            details=response,
            evidence=[
                {
                    "acquisition_line": line,
                    "owner": func_name,
                    "resource": var_name,
                    "missing_event": "close / __exit__",
                }
            ],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
