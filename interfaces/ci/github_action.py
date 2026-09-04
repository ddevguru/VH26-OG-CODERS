import sys
from pathlib import Path
from typing import Optional, Union

from core.common.config import LeakGuardConfig
from core.common.models import Severity, Confidence, ScanResult
from services.scan.scanner import ProjectScanner
from services.policy.engine import PolicyEngine
from presentation.sarif.exporter import SarifExporter


def format_github_annotation(diag) -> str:
    level = "error" if diag.severity in (Severity.ERROR, Severity.CRITICAL) else "warning"
    file_p = diag.file_path.replace("\\", "/")
    line = diag.location.start.line
    col = diag.location.start.column
    title = f"Resource Leak ({diag.resource_type})"
    msg = f"{diag.classification.value}: {diag.reason}"
    return f"::{level} file={file_p},line={line},col={col},title={title}::{msg}"


def run_github_action_ci(
    target_path: Union[str, Path] = ".",
    fail_on: str = "error",
    sarif_out: Optional[str] = "leakguard-results.sarif",
    confidence_threshold: float = 0.85,
) -> int:
    """Executes LeakGuard within a GitHub Action composite step environment."""
    config = LeakGuardConfig(
        fail_on=fail_on,
        report_file=sarif_out,
        output_format="sarif" if sarif_out else "text",
    )
    scanner = ProjectScanner(config)
    scan_result = scanner.scan_directory(target_path)

    if sarif_out:
        SarifExporter().write_sarif_file(scan_result, sarif_out)

    policy_engine = PolicyEngine(config)
    policy_result = policy_engine.evaluate(scan_result)

    # Print GitHub Action workflow annotations
    for diag in scan_result.diagnostics:
        print(format_github_annotation(diag))

    if not policy_result.passed:
        print("\n::error::LeakGuard CI Policy Violation!")
        for r in policy_result.reasons:
            print(f"::error::{r}")
        return 1

    return 0


run_github_action = run_github_action_ci


if __name__ == "__main__":

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(run_github_action_ci(target))
