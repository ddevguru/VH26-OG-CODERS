from pathlib import Path
from typing import List, Union, Optional, Tuple
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, ScanResult, ScanStatistics, Severity, Confidence
from core.common.logger import get_logger
from core.analysis.engine import AnalysisEngine
from services.scan.ignore import IgnoreFilter
from services.baseline.engine import BaselineEngine

logger = get_logger("leakguard.scanner")


class ProjectScanner:
    """Orchestrates multi-file discovery, ignore filtering, parallel worker execution, and baseline suppression across Python projects."""

    def __init__(self, config: Optional[LeakGuardConfig] = None) -> None:
        self.config = config or LeakGuardConfig()
        self.engine = AnalysisEngine(self.config)

    def _get_git_changed_files(self, root: Path) -> List[Path]:
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(root if root.is_dir() else root.parent),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode != 0:
                return []
            changed: List[Path] = []
            base_dir = root if root.is_dir() else root.parent
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    rel = parts[1].strip('"')
                    p = base_dir / rel
                    if p.is_file() and p.suffix == ".py":
                        changed.append(p)
            return changed
        except Exception as e:
            logger.warning(f"Failed to get git changed files: {e}")
            return []

    def discover_files(self, target_path: Union[str, Path]) -> Tuple[List[Path], int]:
        path = Path(target_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Target path '{target_path}' does not exist.")

        if path.is_file():
            if path.suffix != ".py":
                return [], 1
            return [path], 0

        root_dir = path
        ignore_filter = IgnoreFilter(
            root_dir=root_dir,
            extra_excludes=self.config.exclude_patterns,
            extra_includes=self.config.include_patterns,
        )

        all_candidates: List[Path] = []
        if self.config.changed_only:
            all_candidates = self._get_git_changed_files(root_dir)
        else:
            all_candidates = list(root_dir.rglob("*.py"))

        discovered: List[Path] = []
        skipped_count = 0

        for file_path in all_candidates:
            if ignore_filter.is_ignored(file_path):
                skipped_count += 1
            else:
                discovered.append(file_path)

        return discovered, skipped_count

    def scan_directory(self, target_path: Union[str, Path]) -> ScanResult:
        start_time = time.time()
        files, skipped_files_count = self.discover_files(target_path)

        logger.info(f"Discovered {len(files)} Python files in '{target_path}' (skipped {skipped_files_count}).")

        all_diagnostics: List[Diagnostic] = []
        total_functions = 0
        total_resources = 0

        def _analyze_single(f_path: Path) -> Tuple[List[Diagnostic], int, int, bool]:
            return self.engine.analyze_file_with_stats(f_path)

        if self.config.workers > 1 and len(files) > 1:
            with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                results = list(executor.map(_analyze_single, files))
            for diags, funcs, res, is_skipped in results:
                if is_skipped:
                    skipped_files_count += 1
                else:
                    all_diagnostics.extend(diags)
                    total_functions += funcs
                    total_resources += res
        else:
            for f_path in files:
                diags, funcs, res, is_skipped = self.engine.analyze_file_with_stats(f_path)
                if is_skipped:
                    skipped_files_count += 1
                else:
                    all_diagnostics.extend(diags)
                    total_functions += funcs
                    total_resources += res

        # Filter by severity and confidence threshold
        filtered_diags: List[Diagnostic] = []
        sev_order = {Severity.INFO: 1, Severity.WARNING: 2, Severity.ERROR: 3, Severity.CRITICAL: 4}
        conf_order = {Confidence.LOW: 1, Confidence.MEDIUM: 2, Confidence.HIGH: 3}

        min_sev_level = sev_order.get(self.config.min_severity, 1)
        min_conf_level = conf_order.get(self.config.min_confidence, 1)

        for diag in all_diagnostics:
            d_sev = sev_order.get(diag.severity, 2)
            d_conf = conf_order.get(diag.confidence, 2)
            if d_sev >= min_sev_level and d_conf >= min_conf_level:
                filtered_diags.append(diag)

        # Baseline suppression
        baseline_suppressed_count = 0
        if self.config.baseline_file:
            baseline_engine = BaselineEngine(self.config.baseline_file)
            filtered_diags, suppressed = baseline_engine.filter_diagnostics(filtered_diags)
            baseline_suppressed_count = len(suppressed)

        duration = time.time() - start_time
        throughput = len(files) / duration if duration > 0 else 0.0

        stats = ScanStatistics(
            files_scanned=len(files),
            files_skipped=skipped_files_count,
            functions_analyzed=total_functions,
            resources_analyzed=total_resources,
            findings_count=len(filtered_diags),
            duration_seconds=round(duration, 3),
            throughput_files_per_sec=round(throughput, 2),
        )

        return ScanResult(
            status="success",
            scanned_files_count=len(files),
            skipped_files_count=skipped_files_count,
            duration_seconds=round(duration, 3),
            diagnostics=filtered_diags,
            statistics=stats,
            baseline_suppressed_count=baseline_suppressed_count,
            policy_passed=True,
        )
