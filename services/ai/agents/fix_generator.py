import re
import time
import difflib
from typing import Dict, Any, Optional
from core.common.models import Diagnostic
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus, FixCandidate
from services.ai.remediator import AIRemediator


class FixGeneratorAgent(BaseAgent):
    """AGENT 5 — FIX GENERATOR AGENT
    
    Generates candidate code fixes (adding with-statement, try/finally, or close()).
    Returns candidate patch diffs without overwriting original source code directly.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("Fix Generator Agent", provider=provider, tracer=tracer)
        self.remediator = AIRemediator()

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        diagnostic: Optional[Diagnostic] = context.get("diagnostic")
        source_code: str = context.get("source_code", "")
        file_name: str = context.get("file_name", "module.py")

        if not diagnostic or not source_code:
            duration = (time.perf_counter() - start) * 1000.0
            res = AgentResult(
                agent_name=self.agent_name,
                status=AgentStatus.SKIPPED,
                summary="No diagnostic provided — candidate patch generation skipped.",
                execution_time_ms=duration,
            )
            self.tracer.log_agent_step(self.agent_name, AgentStatus.SKIPPED, duration, res.summary)
            return res

        # Generate candidate patch via AIRemediator or LLM
        prompt = (
            f"FIX_GENERATOR_PROMPT\n"
            f"Fix unclosed resource leak at line {diagnostic.location.start.line if diagnostic.location else 1} "
            f"for resource '{diagnostic.resource_variable or 'handle'}' ({diagnostic.resource_type}).\n"
            f"Rule: {diagnostic.rule_id}\n\n"
            f"Original Python Code:\n{source_code}\n\n"
            f"Return ONLY the updated valid Python code enclosed in ```python``` blocks."
        )

        llm_response, _ = self._execute_prompt(prompt, system_prompt="You are an expert Python refactoring agent.")

        # Extract code block from LLM response or fallback to local AST synthesizer
        candidate_code = None
        if "```python" in llm_response:
            match = re.search(r"```python\s*([\s\S]+?)\s*```", llm_response)
            if match:
                candidate_code = match.group(1).strip()

        if not candidate_code:
            # Fallback to deterministic AST Synthesizer
            synth_res = self.remediator.generate_candidate_patch(source_code, diagnostic)
            candidate_code = synth_res.candidate_code

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                source_code.splitlines(keepends=True),
                candidate_code.splitlines(keepends=True),
                fromfile=f"a/{file_name}",
                tofile=f"b/{file_name}",
            )
        )
        unified_diff = "".join(diff_lines)

        duration = (time.perf_counter() - start) * 1000.0

        fix_candidate = FixCandidate(
            finding_id=diagnostic.finding_id,
            original_code=source_code,
            candidate_patch=candidate_code,
            unified_diff=unified_diff,
            explanation=f"Refactored resource '{diagnostic.resource_variable or 'handle'}' to guarantee cleanup.",
            provider=self.provider.provider_name,
        )

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=diagnostic.finding_id,
            summary=f"Generated candidate patch for finding {diagnostic.finding_id}",
            details=unified_diff,
            evidence=[fix_candidate.model_dump()],
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
