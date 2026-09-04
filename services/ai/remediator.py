import ast
import os
import re
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel

from core.common.models import Diagnostic, Classification


class RemediationResult(BaseModel):
    explanation: str
    suggested_fix: str
    candidate_code: str
    is_ai_generated: bool = False
    provider: str = "Local AST Pattern Synthesizer"


class AIRemediator:
    """Optional AI & Synthesizer Remediation Engine for LeakGuard.
    
    GUARANTEE: AI is NEVER used for leak detection. Detection is 100% deterministic
    static analysis (AST + CFG + Dataflow + Resource Semantics).
    AI provides optional explanations and candidate patch generation.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "auto") -> None:
        self.api_key = api_key or os.getenv("LEAKGUARD_LLM_API_KEY")
        self.provider = provider

    def explain_finding(self, diagnostic: Diagnostic) -> str:
        rule = diagnostic.rule_id
        res_type = diagnostic.resource_type
        line = diagnostic.location.start.line if diagnostic.location else 1
        var = diagnostic.resource_variable or "handle"

        explanation = (
            f"LeakGuard AST static analysis detected an unclosed {res_type} resource '{var}' "
            f"acquired at line {line} under rule '{rule}'. "
        )

        if diagnostic.classification == Classification.DEFINITE_LEAK:
            explanation += (
                f"The resource variable '{var}' is assigned without an enclosing context manager ('with' or 'async with') "
                "or matching release call (e.g. .close() / .cleanup()), causing a definite resource leak when control leaves scope."
            )
        else:
            explanation += (
                f"The resource variable '{var}' may leak along conditional branches or early return paths "
                "where cleanup calls are bypassed."
            )

        return explanation

    def generate_candidate_patch(self, source_code: str, diagnostic: Diagnostic) -> RemediationResult:
        explanation = self.explain_finding(diagnostic)

        # Attempt LLM generation if API key is set
        if self.api_key:
            try:
                llm_patch = self._query_llm_patch(source_code, diagnostic)
                if llm_patch:
                    return RemediationResult(
                        explanation=explanation,
                        suggested_fix="AI-Generated Context Manager Refactoring",
                        candidate_code=llm_patch,
                        is_ai_generated=True,
                        provider="LLM Provider API",
                    )
            except Exception:
                pass  # Fallback to local synthesizer

        # Local AST / Synthesizer Fallback
        candidate_code, fix_desc = self._synthesize_local_patch(source_code, diagnostic)
        return RemediationResult(
            explanation=explanation,
            suggested_fix=fix_desc,
            candidate_code=candidate_code,
            is_ai_generated=False,
            provider="Local AST Pattern Synthesizer",
        )

    def _query_llm_patch(self, source_code: str, diagnostic: Diagnostic) -> Optional[str]:
        # Minimal LLM call stub (HTTP post to OpenAI/Anthropic format if key set)
        import httpx
        url = os.getenv("LEAKGUARD_LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        model = os.getenv("LEAKGUARD_LLM_MODEL", "gpt-4o-mini")

        prompt = (
            f"Fix the unclosed resource leak at line {diagnostic.location.start.line if diagnostic.location else 1} "
            f"for rule {diagnostic.rule_id}. Return ONLY the corrected valid Python code.\n\nCode:\n{source_code}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                # Strip markdown block if present
                clean = re.sub(r"^```python\s*", "", text, flags=re.MULTILINE)
                clean = re.sub(r"^```\s*$", "", clean, flags=re.MULTILINE).strip()
                return clean
        return None

    def _synthesize_local_patch(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        lines = source_code.splitlines()
        target_line_idx = (diagnostic.location.start.line - 1) if (diagnostic.location and diagnostic.location.start) else 0

        if target_line_idx >= len(lines):
            return source_code, "No patch synthesized"

        target_line = lines[target_line_idx]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = " " * indent

        # Check for assignment pattern: var = resource_call(...)
        match_assign = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*(.+)$", target_line)
        if match_assign:
            leading_ws, var_name, expr = match_assign.groups()

            # Remove manual close calls downstream if present
            new_lines = []
            for i, l in enumerate(lines):
                if i == target_line_idx:
                    new_lines.append(f"{leading_ws}with {expr} as {var_name}:")
                elif i > target_line_idx:
                    # Indent downstream code in the same scope block
                    if l.strip().startswith(f"{var_name}.close()"):
                        continue  # Skip redundant close inside with block
                    if l.strip() and len(l) - len(l.lstrip()) == indent:
                        new_lines.append(f"    {l}")
                    else:
                        new_lines.append(l)
                else:
                    new_lines.append(l)

            patched = "\n".join(new_lines)
            if source_code.endswith("\n"):
                patched += "\n"
            return patched, f"Converted '{var_name} = {expr}' to 'with {expr} as {var_name}:' context manager."

        # Check for standalone resource call: resource_call(...)
        match_call = re.match(r"^(\s*)(.+)$", target_line)
        if match_call:
            leading_ws, expr = match_call.groups()
            new_lines = lines[:target_line_idx]
            new_lines.append(f"{leading_ws}with {expr}:")
            for l in lines[target_line_idx + 1:]:
                if l.strip() and len(l) - len(l.lstrip()) == indent:
                    new_lines.append(f"    {l}")
                else:
                    new_lines.append(l)

            patched = "\n".join(new_lines)
            if source_code.endswith("\n"):
                patched += "\n"
            return patched, f"Wrapped '{expr.strip()}' inside context manager block."

        return source_code, "Unchanged"
