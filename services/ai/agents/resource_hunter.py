import time
from typing import Dict, Any, Optional
from core.common.models import Diagnostic, Classification
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


class ResourceHunterAgent(BaseAgent):
    """AGENT 1 — RESOURCE HUNTER
    
    GUARANTEE: The Resource Hunter must NOT replace the deterministic analyzer.
    Receives deterministic findings and enriches them with resource context,
    surrounding code explanation, ownership interpretation, and lifecycle patterns.
    If deterministic analyzer says SAFE, the AI must NOT invent a leak.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Resource Hunter", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")
        source_code: str = context.get("source_code", "")

        if not diagnostic:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.COMPLETED,
                summary="No resource leak identified by deterministic analysis.",
                details="Deterministic static analysis confirmed resource safety. AI Hunter did not invent findings.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
            return res

        # Safety Check: If SAFE, return clean report
        if diagnostic.classification == Classification.SAFE:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.COMPLETED,
                finding_id=diagnostic.finding_id,
                summary="Resource lifecycle verified SAFE by deterministic AST solver.",
                details="Code exhibits full acquisition and matching release semantics.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
            return res

        # Build prompt for enriching findings
        prompt = (
            f"RESOURCE_HUNTER_ENRICHMENT\n"
            f"Analyze finding for resource '{diagnostic.resource_variable or 'handle'}' of type '{diagnostic.resource_type}'.\n"
            f"Rule: {diagnostic.rule_id}\n"
            f"Classification: {diagnostic.classification.value}\n"
            f"File: {diagnostic.file_path}\n"
            f"Location: Line {diagnostic.location.start.line if diagnostic.location else 1}\n"
            f"Reason: {diagnostic.reason}\n\n"
            f"Code Snippet:\n{source_code}\n\n"
            f"Provide a concise summary of the resource context, scope, and missing lifecycle release."
        )

        response, duration = self._execute_prompt(prompt, system_prompt="You are a resource lifecycle enrichment agent.")

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=diagnostic.finding_id,
            summary=f"Tracked unclosed resource '{diagnostic.resource_variable or 'handle'}' ({diagnostic.resource_type})",
            details=response,
            recommendations=[f"Ensure '{diagnostic.resource_variable or 'handle'}' is closed via with-statement or finally block."],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
