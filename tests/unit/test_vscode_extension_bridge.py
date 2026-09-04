import json
import pytest
from pathlib import Path

from core.analysis.engine import AnalysisEngine
from core.common.config import LeakGuardConfig
from services.scan.scanner import ProjectScanner


def test_engine_bridge_json_output_structure(tmp_path):
    # Create sample Python file with resource leak
    test_file = tmp_path / "sample_leak.py"
    test_file.write_text(
        "def leaky_func():\n"
        "    f = open('data.txt')\n"
        "    if not f:\n"
        "        return\n"
        "    f.close()\n"
    )

    config = LeakGuardConfig(output_format="json")
    scanner = ProjectScanner(config)
    scan_result = scanner.scan_directory(tmp_path)

    # Convert to JSON dictionary format used by VS Code extension bridge
    from presentation.json.exporter import JsonExporter
    exporter = JsonExporter()
    json_dict = exporter.to_json_dict(scan_result)

    diags_list = json_dict.get("findings") or json_dict.get("diagnostics")
    assert diags_list is not None
    assert len(diags_list) >= 1

    diag = diags_list[0]
    assert "rule_id" in diag
    assert "severity" in diag
    assert "confidence" in diag
    assert "classification" in diag
    assert "location" in diag
    assert "start" in diag["location"]
    assert diag["location"]["start"]["line"] == 2
    assert "message" in diag or "reason" in diag
    assert "fingerprint" in diag
