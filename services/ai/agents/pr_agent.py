import time
from typing import Dict, Any, List
from services.ai.agents.base_agent import BaseAgent
from services.ai.models import AgentResult, AgentStatus, ReviewResult


class PRAgent(BaseAgent):
    """AGENT 8 — PR AGENT
    
    Responsible for Pull Request & Commit review formatting, summary generation,
    inline comment mapping, and overall resource safety status calculation.
    """

    def __init__(self, provider=None, tracer=None) -> None:
        super().__init__("PR Agent", provider=provider, tracer=tracer)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        start = time.perf_counter()
        files_count = context.get("files_count", 1)
        new_leaks = context.get("new_leaks", 0)
        resolved_leaks = context.get("resolved_leaks", 0)
        verified_fixes = context.get("verified_fixes", 0)
        pr_number = context.get("pr_number", "PR #1")
        commit_sha = context.get("commit_sha", "")

        is_passed = new_leaks == 0
        overall = "🟢 Resource Safety Passed" if is_passed else "❌ Resource Safety Failed"

        summary_lines = [
            f"LeakGuard AI Review — {pr_number}" if not commit_sha else f"Commit {commit_sha[:8]} Review",
            "────────────────────────────────────────",
            f"Files analyzed:   {files_count}",
            f"New leaks:        🔴 {new_leaks}",
            f"Resolved leaks:   🟢 {resolved_leaks}",
            f"Verified AI fixes: ✓ {verified_fixes}",
            "",
            f"Result: {overall}",
        ]
        summary = "\n".join(summary_lines)

        duration = (time.perf_counter() - start) * 1000.0

        res = AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.COMPLETED,
            summary=overall,
            details=summary,
            execution_time_ms=duration,
        )

        self.tracer.log_agent_step(self.agent_name, AgentStatus.COMPLETED, duration, res.summary)
        return res
