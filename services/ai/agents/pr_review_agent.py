"""PR Review Agent — AI explanations for LeakGuard deterministic findings.

CRITICAL CONSTRAINT:
  - AI receives deterministic findings only.
  - AI output is EXPLANATORY ONLY.
  - AI cannot change classification (DEFINITE/POTENTIAL/SAFE).
  - AI cannot change risk score.
  - AI confidence is informational only — not authoritative.

Output schema:
{
    "finding_id": "LG-102",
    "summary": "Database connection acquired on line 42 is not closed on the exception path.",
    "root_cause": "The connection is opened before a block that may raise an exception, with no finally clause.",
    "impact": "Connection pool exhaustion under load, leading to application-level hang.",
    "recommended_strategy": "try_finally",
    "confidence": 0.94
}
"""
import json
import time
from typing import Any, Dict

from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus


STRATEGY_DESCRIPTIONS = {
    "context_manager": "Wrap the resource acquisition in a `with` statement",
    "try_finally": "Use `try/finally` to guarantee cleanup on all paths",
    "explicit_close": "Add explicit `.close()` call before function exit",
    "async_context_manager": "Use `async with` for async resource management",
}


class PRReviewAgent(BaseAgent):
    """AGENT — PR Review Agent

    Provides structured AI explanations for LeakGuard deterministic findings.
    Cannot classify code as safe or leak. Cannot modify risk scores.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("PR Review Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()

        finding_id = context.get("finding_id", "unknown")
        classification = context.get("classification", "DEFINITE_LEAK")
        rule_id = context.get("rule_id", "")
        file_path = context.get("file_path", "")
        line_number = context.get("line_number", 0)
        resource_type = context.get("resource_type", "FILE")
        resource_variable = context.get("resource_variable", "resource")
        message = context.get("message", "")
        reason = context.get("reason", "")

        prompt = f"""You are a senior Python security engineer reviewing a resource leak finding from LeakGuard static analysis.

FINDING (deterministic, authoritative — you cannot change this):
- ID: {finding_id}
- Classification: {classification}
- Rule: {rule_id}
- File: {file_path}
- Line: {line_number}
- Resource type: {resource_type}
- Variable: {resource_variable}
- Problem: {message}
- Detail: {reason}

Your task is to provide a STRUCTURED JSON explanation with these exact fields:
{{
    "finding_id": "{finding_id}",
    "summary": "One sentence plain-English summary of the finding",
    "root_cause": "Technical root cause analysis (2-3 sentences)",
    "impact": "What could happen in production if this is not fixed (2-3 sentences)",
    "recommended_strategy": "One of: context_manager, try_finally, explicit_close, async_context_manager",
    "confidence": 0.9
}}

RULES:
- Do NOT say the code is safe.
- Do NOT say there is no leak.
- Do NOT change the classification.
- Keep response as valid JSON only, no extra text.
- confidence is how confident you are in your explanation (0.0-1.0), not in leak existence.
"""

        try:
            raw, _ = self._execute_prompt(prompt, temperature=0.0)
            explanation = self._parse_json(raw, finding_id)
        except Exception as e:
            explanation = self._fallback_explanation(context, str(e))

        duration = (time.perf_counter() - start) * 1000.0

        result = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            finding_id=finding_id,
            summary=explanation.get("summary", message),
            details=json.dumps(explanation),
            execution_time_ms=duration,
        )
        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, result.summary)
        return result

    def _parse_json(self, raw: str, finding_id: str) -> Dict[str, Any]:
        """Parse JSON from AI response, with best-effort extraction."""
        raw = raw.strip()
        # Find JSON block
        start_idx = raw.find("{")
        end_idx = raw.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = raw[start_idx:end_idx]
            data = json.loads(json_str)
            # Validate required fields
            data.setdefault("finding_id", finding_id)
            data.setdefault("summary", "Resource leak detected.")
            data.setdefault("root_cause", "Resource not properly closed.")
            data.setdefault("impact", "Potential resource exhaustion.")
            data.setdefault("recommended_strategy", "try_finally")
            data.setdefault("confidence", 0.8)
            # Clamp confidence
            data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
            return data
        raise ValueError("No JSON found in AI response")

    def _fallback_explanation(
        self, context: Dict[str, Any], error: str
    ) -> Dict[str, Any]:
        """Provide a deterministic fallback explanation when AI is unavailable."""
        resource_type = context.get("resource_type", "resource").upper()
        resource_variable = context.get("resource_variable", "resource")
        line_number = context.get("line_number", "?")

        resource_map = {
            "DATABASE": ("database connection", "connection pool exhaustion", "try_finally"),
            "FILE": ("file handle", "file descriptor exhaustion", "context_manager"),
            "SOCKET": ("network socket", "socket descriptor exhaustion", "try_finally"),
            "HTTP": ("HTTP session", "connection pool exhaustion", "context_manager"),
            "SUBPROCESS": ("subprocess handle", "zombie process accumulation", "try_finally"),
        }
        res_desc, impact_desc, strategy = resource_map.get(
            resource_type.replace("RESOURCETYPE.", ""),
            ("resource", "resource exhaustion", "try_finally"),
        )

        return {
            "finding_id": context.get("finding_id", "unknown"),
            "summary": f"The {res_desc} `{resource_variable}` acquired at line {line_number} is not guaranteed to be closed on all execution paths.",
            "root_cause": f"The {res_desc} is opened but the cleanup code is not inside a `try/finally` block or context manager, meaning an exception on any code path between acquisition and close will cause the resource to leak.",
            "impact": f"In production, this can cause {impact_desc} leading to degraded performance or application unavailability.",
            "recommended_strategy": strategy,
            "confidence": 0.75,
        }
