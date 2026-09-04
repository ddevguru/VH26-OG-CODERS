from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification
from core.common.logger import get_logger

logger = get_logger("leakguard.diff")


class PRDiffResult(BaseModel):
    pr_number: Optional[str] = None
    before_count: int
    after_count: int
    resolved_count: int
    new_count: int
    potential_delta: int
    status_summary: str = ""
    resolved_findings: List[Diagnostic] = Field(default_factory=list)
    new_findings: List[Diagnostic] = Field(default_factory=list)
    unchanged_findings: List[Diagnostic] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PRDiffEngine:
    """Engine comparing resource leak findings between PR Base commit vs Head commit."""

    def compare(
        self,
        before: List[Diagnostic],
        after: List[Diagnostic],
        pr_number: Optional[str] = None,
    ) -> PRDiffResult:
        before_fps: Dict[str, Diagnostic] = {d.fingerprint: d for d in before}
        after_fps: Dict[str, Diagnostic] = {d.fingerprint: d for d in after}

        resolved: List[Diagnostic] = []
        new_findings: List[Diagnostic] = []
        unchanged: List[Diagnostic] = []

        # Find resolved (in before but not in after)
        for fp, diag in before_fps.items():
            if fp not in after_fps:
                resolved.append(diag)
            else:
                unchanged.append(after_fps[fp])

        # Find new (in after but not in before)
        for fp, diag in after_fps.items():
            if fp not in before_fps:
                new_findings.append(diag)

        # Count potential leaks delta
        before_potential = sum(1 for d in before if d.classification == Classification.POTENTIAL_LEAK)
        after_potential = sum(1 for d in after if d.classification == Classification.POTENTIAL_LEAK)
        potential_delta = after_potential - before_potential

        summary = f"🟢 {len(resolved)} leaks fixed, 🔴 {len(new_findings)} new leaks introduced."

        return PRDiffResult(
            pr_number=pr_number,
            before_count=len(before),
            after_count=len(after),
            resolved_count=len(resolved),
            new_count=len(new_findings),
            potential_delta=potential_delta,
            status_summary=summary,
            resolved_findings=resolved,
            new_findings=new_findings,
            unchanged_findings=unchanged,
        )
