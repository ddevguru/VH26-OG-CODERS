from pathlib import Path
from typing import List, Union, Optional

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, ScanResult
from services.scan.scanner import ProjectScanner
from core.analysis.engine import AnalysisEngine


class LeakGuardAPI:
    """Programmatic Python API for embedding LeakGuard in automated Python pipelines."""

    def __init__(self, config: Optional[LeakGuardConfig] = None) -> None:
        self.config = config or LeakGuardConfig()
        self.scanner = ProjectScanner(self.config)
        self.engine = AnalysisEngine(self.config)

    def scan_path(self, target_path: Union[str, Path]) -> ScanResult:
        path = Path(target_path)
        diagnostics = self.scanner.scan_directory(path) if path.is_dir() else self.engine.analyze_file(path)

        return ScanResult(
            status="success",
            scanned_files_count=len(self.scanner.discover_files(path)) if path.is_dir() else 1,
            duration_seconds=0.0,
            diagnostics=diagnostics,
            policy_passed=not any(d.severity == self.config.fail_on_severity for d in diagnostics),
        )

    def scan_code(self, source_code: str, file_name: str = "<stdin>") -> List[Diagnostic]:
        return self.engine.analyze_source_code(source_code, file_name)
