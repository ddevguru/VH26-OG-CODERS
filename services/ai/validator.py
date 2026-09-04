import ast
import difflib
import os
import tempfile
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from core.analysis.engine import AnalysisEngine
from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification


class ValidationReport(BaseModel):
    is_valid: bool = False
    original_finding_cleared: bool = False
    new_findings_count: int = 0
    syntax_valid: bool = False
    unified_diff: str = ""
    validation_steps: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    requires_human_approval: bool = True


class PatchValidator:
    """9-Step AST Patch Validation Engine for LeakGuard.
    
    Validates every candidate patch (LLM or synthesized) in an isolated workspace
    before proposing it for human approval.
    """

    def __init__(self, config: Optional[LeakGuardConfig] = None) -> None:
        self.config = config or LeakGuardConfig()
        self.engine = AnalysisEngine(self.config)

    def validate_patch(
        self,
        original_source: str,
        candidate_source: str,
        target_diagnostic: Diagnostic,
        file_name: str = "target_module.py",
    ) -> ValidationReport:
        report = ValidationReport()
        steps = report.validation_steps

        # Compute Unified Diff (Step 8 preview)
        diff_lines = list(
            difflib.unified_diff(
                original_source.splitlines(keepends=True),
                candidate_source.splitlines(keepends=True),
                fromfile=f"a/{file_name}",
                tofile=f"b/{file_name}",
            )
        )
        report.unified_diff = "".join(diff_lines)

        # Step 3 & 7: Verify Syntax & Parse AST
        steps.append("Step 3 & 7: Parse Python AST & Verify Syntax")
        try:
            ast.parse(candidate_source, filename=file_name)
            report.syntax_valid = True
        except SyntaxError as se:
            report.syntax_valid = False
            report.is_valid = False
            report.failure_reason = f"Syntax error in candidate patch at line {se.lineno}: {se.msg}"
            return report

        # Step 1: Create Isolated Workspace
        steps.append("Step 1: Create Isolated Workspace Directory")
        with tempfile.TemporaryDirectory(prefix="leakguard_val_") as tmp_dir:
            tmp_path = Path(tmp_dir) / file_name

            # Step 2: Apply Patch to Isolated Workspace
            steps.append("Step 2: Apply Candidate Patch to Isolated File")
            tmp_path.write_text(candidate_source, encoding="utf-8")

            # Step 4: Run LeakGuard Static Analysis
            steps.append("Step 4: Execute LeakGuard Static Analysis on Patched Code")
            patched_diagnostics = self.engine.analyze_file(tmp_path)

            # Step 5: Verify Original Finding Disappears
            steps.append("Step 5: Verify Target Leak Finding Disappears")
            original_cleared = True
            for d in patched_diagnostics:
                if (
                    d.rule_id == target_diagnostic.rule_id
                    and d.classification == target_diagnostic.classification
                ):
                    original_cleared = False
                    break

            report.original_finding_cleared = original_cleared

            # Step 6: Verify No New Blocking Findings
            steps.append("Step 6: Verify No New Leaks Introduced")
            blocking_leaks = [
                d for d in patched_diagnostics
                if d.classification in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK)
            ]
            report.new_findings_count = len(blocking_leaks)

            # Evaluation
            if not report.original_finding_cleared:
                report.is_valid = False
                report.failure_reason = "Original leak finding was not cleared by the patch."
            elif report.new_findings_count > 0:
                report.is_valid = False
                report.failure_reason = f"Patch introduced {report.new_findings_count} new leak findings."
            else:
                report.is_valid = True
                steps.append("Step 9: Passed All Automated Checks — Human Approval Required")

        return report
