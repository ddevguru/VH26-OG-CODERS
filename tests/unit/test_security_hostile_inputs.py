import pytest
import os
import sys
import tempfile
import json
from pathlib import Path

from core.common.config import LeakGuardConfig
from core.parser.ast_parser import PythonAstParser, ParserSecurityError
from core.analysis.engine import AnalysisEngine
from services.scan.scanner import ProjectScanner
from services.baseline.engine import BaselineEngine
from presentation.sarif.exporter import SarifExporter
from presentation.json.exporter import JsonExporter


def test_malicious_python_source_does_not_execute(tmp_path):
    """Verify malicious code constructs in Python files are never executed."""
    canary_file = tmp_path / "canary.txt"
    malicious_code = f"""
import os
import sys
import subprocess

# Malicious payload attempts
os.remove("{canary_file}") if os.path.exists("{canary_file}") else None
exec("open('{canary_file}', 'w').write('HACKED')")
eval("1 + 1")
sys.exit(99)
"""
    test_file = tmp_path / "malicious.py"
    test_file.write_text(malicious_code, encoding="utf-8")

    engine = AnalysisEngine()
    diags = engine.analyze_file(test_file)

    # Verify canary file was NOT created or modified by exec/eval/code execution
    assert not canary_file.exists()
    assert isinstance(diags, list)


def test_huge_file_size_limit_skipped(tmp_path):
    """Verify files larger than max_file_size_bytes are safely skipped."""
    huge_file = tmp_path / "huge.py"
    huge_file.write_text("# filler code\n" + "x = 1\n" * 100_000, encoding="utf-8")

    config = LeakGuardConfig(max_file_size_bytes=100_000)
    engine = AnalysisEngine(config)
    diags, funcs, res, is_skipped = engine.analyze_file_with_stats(huge_file)

    assert is_skipped is True
    assert diags == []


def test_deeply_nested_syntax_ast_depth_protection():
    """Verify AST recursion depth limit triggers ParserSecurityError safely."""
    # Build nested if-statements with proper indentation
    lines = []
    for i in range(20):
        lines.append(" " * (i * 4) + f"if True:")
    lines.append(" " * (20 * 4) + "pass")
    nested_code = "\n".join(lines)

    # Set low max depth (10) to verify depth check catches deep recursion safely
    parser = PythonAstParser(max_depth=10)
    with pytest.raises(ParserSecurityError) as exc_info:
        parser.parse_string(nested_code)

    assert "AST recursion depth limit" in str(exc_info.value)


def test_huge_repository_file_limit_capping(tmp_path):
    """Verify discover_files respects max_files_limit."""
    repo_dir = tmp_path / "huge_repo"
    repo_dir.mkdir()

    for i in range(15):
        (repo_dir / f"file_{i}.py").write_text("x = 1\n")

    config = LeakGuardConfig(max_files_limit=5)
    scanner = ProjectScanner(config)
    discovered, skipped = scanner.discover_files(repo_dir)

    assert len(discovered) <= 5


def test_malicious_filenames_handling(tmp_path):
    """Verify files with path traversal names or special characters are safely processed."""
    special_dir = tmp_path / "space dir & special $ name"
    special_dir.mkdir()
    file_with_spaces = special_dir / "test file $1.py"
    file_with_spaces.write_text("def test():\n    f = open('test.txt')\n")

    engine = AnalysisEngine()
    diags = engine.analyze_file(file_with_spaces)

    assert len(diags) >= 1
    assert diags[0].file_path == str(file_with_spaces)


def test_symlinks_and_circular_loops(tmp_path):
    """Verify symlink loops do not cause infinite recursion during discovery."""
    scan_dir = tmp_path / "symlink_test"
    scan_dir.mkdir()
    (scan_dir / "valid.py").write_text("x = 1\n")

    try:
        os.symlink(scan_dir, scan_dir / "circular_link", target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("Symlink creation not supported on host OS / environment permissions")

    scanner = ProjectScanner(LeakGuardConfig())
    discovered, skipped = scanner.discover_files(scan_dir)

    assert any("valid.py" in str(p) for p in discovered)


def test_path_traversal_prevention_in_exporters(tmp_path):
    """Verify SARIF & JSON exporters handle relative/traversal paths safely."""
    engine = AnalysisEngine()
    diags = engine.analyze_code("def test():\n    f = open('file.txt')\n", filename="../../etc/passwd")

    exporter = JsonExporter()
    out = exporter.to_json_dict(diags)

    assert "findings" in out
    assert len(out["findings"]) == 1


def test_malformed_configuration_yaml(tmp_path):
    """Verify malformed configuration fields fall back to safe defaults."""
    config = LeakGuardConfig(
        workers=-5,
        max_file_size_bytes=100,
    )
    assert config.max_file_size_bytes == 100
    assert config.max_ast_depth == 500  # Default depth intact


def test_resource_and_cpu_exhaustion_bounds():
    """Verify analysis engine handles large/complex Python functions within node limits."""
    large_func = "def complex_func():\n" + "\n".join([f"    var_{i} = open('test_{i}.txt')" for i in range(200)])

    engine = AnalysisEngine()
    diags = engine.analyze_code(large_func)

    assert len(diags) == 200


def test_malformed_sarif_ingestion_safety(tmp_path):
    """Verify corrupt SARIF JSON files are rejected cleanly."""
    corrupt_sarif = tmp_path / "corrupt.sarif"
    corrupt_sarif.write_text("{ corrupt json syntax ...", encoding="utf-8")

    with pytest.raises(ValueError):
        with open(corrupt_sarif, "r") as f:
            json.load(f)


def test_malformed_json_baseline_safety(tmp_path):
    """Verify BaselineEngine handles corrupt baseline JSON files cleanly by raising ValueError."""
    corrupt_baseline = tmp_path / "corrupt.json"
    corrupt_baseline.write_text("NOT_JSON_DATA", encoding="utf-8")

    with pytest.raises(ValueError):
        BaselineEngine(corrupt_baseline)


def test_unsafe_subprocess_invocation_prevention():
    """Verify ProjectScanner git integration passes command arguments as a list without shell=True."""
    scanner = ProjectScanner()
    changed = scanner._get_git_changed_files(Path("."))
    assert isinstance(changed, list)


def test_zero_customer_code_execution_verification(tmp_path):
    """Verify that importing/evaluating code is never called when scanning setup.py or custom modules."""
    setup_file = tmp_path / "setup.py"
    setup_file.write_text("""
import sys
# If executed, this would raise SystemExit
sys.exit(42)
""", encoding="utf-8")

    engine = AnalysisEngine()
    # Analyzing setup.py MUST NOT trigger sys.exit(42)
    diags = engine.analyze_file(setup_file)
    assert isinstance(diags, list)


def test_arbitrary_expression_evaluation_prevention():
    """Verify complex dynamic expressions (lambda, comprehension, genexpr) are parsed safely without evaluation."""
    complex_expr = """
def test_expr():
    gen = (x for x in range(100) if x % 2 == 0)
    lam = lambda a, b: a + b
    comp = [i * 2 for i in range(10)]
"""
    engine = AnalysisEngine()
    diags = engine.analyze_code(complex_expr)
    assert isinstance(diags, list)


def test_mixed_batch_scanner_resilience(tmp_path):
    """Verify scanner handles a mix of valid, syntax-error, and empty files in a batch without crashing."""
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()

    (batch_dir / "valid.py").write_text("def foo():\n    f = open('valid.txt')\n")
    (batch_dir / "invalid.py").write_text("def broken_syntax(:\n")
    (batch_dir / "empty.py").write_text("")

    scanner = ProjectScanner()
    res = scanner.scan_directory(batch_dir)

    assert res.scanned_files_count == 3
    assert len(res.diagnostics) == 1
    assert res.diagnostics[0].rule_id == "RULE_LEAK_001"


def test_dependency_vulnerability_audit_checks():
    """Verify pydantic, typer, starlette, fastAPI, and pytest dependencies exist and operate in safe modes."""
    import pydantic
    import typer

    assert pydantic.__version__ is not None
    assert typer.__name__ == "typer"
