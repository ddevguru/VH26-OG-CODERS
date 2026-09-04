import os
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from interfaces.cli.main import app

runner = CliRunner()


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    proj = tmp_path / "test_proj"
    proj.mkdir()

    safe_file = proj / "safe.py"
    safe_file.write_text("""
def read_data():
    with open('data.txt') as f:
        return f.read()
""", encoding="utf-8")

    leak_file = proj / "leak.py"
    leak_file.write_text("""
def leak_data():
    f = open('data.txt')
    return f.read()
""", encoding="utf-8")

    ignored_file = proj / "ignored.py"
    ignored_file.write_text("""
def leak_ignored():
    f = open('ignored.txt')
    return f.read()
""", encoding="utf-8")

    return proj


def test_cli_scan_single_safe_file(temp_project: Path):
    safe_py = temp_project / "safe.py"
    result = runner.invoke(app, ["scan", str(safe_py)])
    assert result.exit_code == 0
    assert "No resource leaks detected" in result.stdout or "Files Scanned" in result.stdout


def test_cli_scan_single_leak_file(temp_project: Path):
    leak_py = temp_project / "leak.py"
    result = runner.invoke(app, ["scan", str(leak_py)])
    assert result.exit_code == 1
    assert "leak.py" in result.stdout or "Scan Failed" in result.stdout


def test_cli_scan_directory(temp_project: Path):
    result = runner.invoke(app, ["scan", str(temp_project)])
    assert result.exit_code == 1
    assert "Scan Performance Statistics" in result.stdout or "leak.py" in result.stdout


def test_cli_scan_format_json(temp_project: Path):
    out_json = temp_project / "report.json"
    result = runner.invoke(app, ["scan", str(temp_project), "--format", "json", "--out", str(out_json)])
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["tool"] == "LeakGuard"
    assert "findings" in data
    assert "statistics" in data


def test_cli_scan_format_sarif(temp_project: Path):
    out_sarif = temp_project / "report.sarif"
    result = runner.invoke(app, ["scan", str(temp_project), "--format", "sarif", "--out", str(out_sarif)])
    assert out_sarif.exists()
    data = json.loads(out_sarif.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert len(data["runs"]) > 0


def test_cli_scan_gitignore_respect(temp_project: Path):
    gitignore = temp_project / ".gitignore"
    gitignore.write_text("leak.py\nignored.py\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(temp_project)])
    # Since leak files are ignored, only safe.py is scanned -> exit code 0
    assert result.exit_code == 0


def test_cli_scan_leakguardignore_respect(temp_project: Path):
    leakguardignore = temp_project / ".leakguardignore"
    leakguardignore.write_text("leak.py\nignored.py\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(temp_project)])
    assert result.exit_code == 0



def test_cli_scan_baseline_suppression(temp_project: Path):
    leak_py = temp_project / "leak.py"
    baseline_file = temp_project / "baseline.json"

    # Step 1: Create baseline
    res1 = runner.invoke(app, ["scan", str(leak_py), "--update-baseline", "--baseline", str(baseline_file), "--fail-on", "none"])
    assert baseline_file.exists()

    # Step 2: Scan with baseline -> findings are suppressed, exit code 0
    res2 = runner.invoke(app, ["scan", str(leak_py), "--baseline", str(baseline_file)])
    assert res2.exit_code == 0


def test_cli_scan_workers_parallel(temp_project: Path):
    result = runner.invoke(app, ["scan", str(temp_project), "--workers", "4", "--fail-on", "none"])
    assert result.exit_code == 0


def test_cli_scan_fail_on_none(temp_project: Path):
    leak_py = temp_project / "leak.py"
    result = runner.invoke(app, ["scan", str(leak_py), "--fail-on", "none"])
    assert result.exit_code == 0


def test_cli_scan_nonexistent_target_exit_code_2():
    result = runner.invoke(app, ["scan", "non_existent_directory_abc123_xyz"])
    assert result.exit_code == 2


def test_cli_scan_quiet_mode(temp_project: Path):
    safe_py = temp_project / "safe.py"
    result = runner.invoke(app, ["scan", str(safe_py), "--quiet"])
    assert result.exit_code == 0
    assert "Scan Performance Statistics" not in result.stdout
