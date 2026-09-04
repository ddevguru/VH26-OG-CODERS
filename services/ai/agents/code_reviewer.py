import time
from typing import Dict, Any, List, Optional
from core.common.models import Diagnostic, Classification
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus, ReviewMode


class CodeReviewerAgent(BaseAgent):
    """AGENT 2 — CODE REVIEW AGENT
    
    Responsibilities:
    - Explain findings across PRs, commits, or files
    - Review affected code & summarize resource lifecycle
    - Distinguish DEFINITE_LEAK, POTENTIAL_LEAK, and SAFE
    - Never upgrade SAFE to a leak based only on AI opinion
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Code Reviewer", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostics: List[Diagnostic] = context.get("diagnostics", [])
        source_code: str = context.get("source_code", "")
        review_mode: ReviewMode = context.get("review_mode", ReviewMode.DETAILED)
        target_name: str = context.get("target_name", "Source File")

        if not diagnostics:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.COMPLETED,
                summary="🟢 Code Review Passed — Zero Resource Leaks Detected.",
                details=f"Deterministic AST static analysis confirmed {target_name} is 100% resource safe.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
            return res

        prompt = (
            f"CODE_REVIEW_AGENT (Mode: {review_mode.value})\n"
            f"Review deterministic resource findings for {target_name}:\n"
        )
        for d in diagnostics:
            func = getattr(d, "function_name", None) or "function"
            line = d.location.start.line if d.location else 1
            prompt += (
                f"- [{d.classification.value}] Rule {d.rule_id} in {d.file_path}:{line} ({func}()): "
                f"Resource '{d.resource_variable or 'handle'}' of type '{d.resource_type}'. Reason: {d.reason}\n"
            )

        prompt += f"\nCode Context:\n{source_code}\n\nGenerate a structured resource safety code review."

        response, duration = self._execute_prompt(prompt, system_prompt="You are a senior Python resource-security code reviewer.")

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            summary=f"Reviewed {len(diagnostics)} resource finding(s) for {target_name}",
            details=response,
            recommendations=["Refactor unclosed resource handles using context managers ('with' statement)."],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
