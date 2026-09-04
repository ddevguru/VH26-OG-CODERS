from typing import List
from pathlib import Path

from core.analysis.engine import AnalysisEngine
from core.common.models import Diagnostic, Classification


def run_precommit_hook(files: List[str]) -> int:
    """Executes fast local scans on staged Python files before commit."""
    engine = AnalysisEngine()
    total_leaks = 0

    for file_str in files:
        path = Path(file_str)
        if path.suffix == ".py":
            diagnostics = engine.analyze_file(path)
            leak_count = sum(1 for d in diagnostics if d.classification in (Classification.DEFINITE_LEAK, Classification.POTENTIAL_LEAK))
            total_leaks += leak_count

    return 1 if total_leaks > 0 else 0
