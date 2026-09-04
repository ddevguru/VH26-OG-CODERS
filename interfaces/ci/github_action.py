from pathlib import Path
from typing import Optional
from core.common.config import LeakGuardConfig
from core.common.models import Severity
from services.scan.scanner import ProjectScanner
from presentation.sarif.exporter import SarifExporter


def run_github_action(
    target_path: str = ".",
    threshold: Severity = Severity.ERROR,
    sarif_out: str = "leakguard-results.sarif",
) -> int:
    """Executes LeakGuard within a GitHub Action composite step environment."""
    config = LeakGuardConfig(fail_on_severity=threshold)
    scanner = ProjectScanner(config)

    diagnostics = scanner.scan_directory(target_path)
    SarifExporter().write_sarif_file(diagnostics, sarif_out)

    return 1 if any(d.severity == threshold for d in diagnostics) else 0
