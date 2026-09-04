from pathlib import Path
import pytest
from core.analysis.engine import AnalysisEngine
from core.common.models import Classification


def test_early_return_leak() -> None:
    engine = AnalysisEngine()
    path = Path("examples/vulnerable/early_return_leak.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 1
    assert diags[0].resource_variable == "f"


def test_exception_path_leak() -> None:
    engine = AnalysisEngine()
    path = Path("examples/vulnerable/exception_path_leak.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 1
    assert diags[0].resource_variable == "conn"


def test_branch_leak() -> None:
    engine = AnalysisEngine()
    path = Path("examples/vulnerable/branch_leak.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 1
    assert diags[0].resource_variable == "s"


def test_with_statement_safe() -> None:
    engine = AnalysisEngine()
    path = Path("examples/safe/with_statement_safe.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 0


def test_try_finally_safe() -> None:
    engine = AnalysisEngine()
    path = Path("examples/safe/try_finally_safe.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 0


def test_returned_resource_safe() -> None:
    engine = AnalysisEngine()
    path = Path("examples/safe/returned_resource_safe.py")
    diags = engine.analyze_file(path)

    assert len(diags) == 0
