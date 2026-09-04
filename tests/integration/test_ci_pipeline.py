import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

from core.common.models import Diagnostic, Classification, Severity, Confidence, Policy, Span, SourceLocation
from services.policy.engine import PolicyEngine
from interfaces.ci.github_action import run_github_action_ci, format_github_annotation
from interfaces.ci.gitlab import GitLabCodeQualityExporter, run_gitlab_ci
from interfaces.ci.jenkins import JenkinsJUnitExporter, run_jenkins_ci
from interfaces.ci.bitbucket import BitbucketCodeInsightsExporter, run_bitbucket_ci
from services.scan.scanner import ProjectScanner
from core.common.config import LeakGuardConfig


@pytest.fixture
def sample_diag() -> Diagnostic:
    return Diagnostic(
        finding_id="LEAK_12345678",
        rule_id="RULE_LEAK_001",
        classification=Classification.DEFINITE_LEAK,
        message="Resource leak detected: 'f' (FILE)",
        file_path="vulnerable/early_return_leak.py",
        location=Span(
            start=SourceLocation(line=2, column=5),
            end=SourceLocation(line=2, column=24),
        ),
        resource_type="FILE",
        resource_variable="f",
        confidence=Confidence.HIGH,
        severity=Severity.ERROR,
        reason="Resource 'f' of type 'FILE' is acquired but never closed on normal execution exit path.",
    )


def test_policy_engine_confidence_threshold_evaluation(sample_diag: Diagnostic):
    policy = Policy(fail_on="high", confidence_threshold=0.85)
    engine = PolicyEngine(policy)

    result = engine.evaluate([sample_diag])
    assert not result.passed
    assert len(result.blocking_findings) == 1

    # Lower confidence diagnostic should be suppressed by policy
    low_conf_diag = sample_diag.model_copy()
    low_conf_diag.confidence = Confidence.LOW

    result_suppressed = engine.evaluate([low_conf_diag])
    assert result_suppressed.passed
    assert len(result_suppressed.blocking_findings) == 0
    assert len(result_suppressed.suppressed_findings) == 1


def test_github_action_ci_runner(sample_diag: Diagnostic, tmp_path: Path):
    sarif_file = tmp_path / "leakguard-results.sarif"
    sample_repo_path = Path("examples/sample_repo")

    annotation = format_github_annotation(sample_diag)
    assert "::error file=vulnerable/early_return_leak.py,line=2,col=5" in annotation

    exit_code = run_github_action_ci(sample_repo_path, fail_on="warning", sarif_out=str(sarif_file))
    assert exit_code == 1
    assert sarif_file.exists()



def test_gitlab_ci_exporter(sample_diag: Diagnostic, tmp_path: Path):
    out_file = tmp_path / "gl-code-quality-report.json"
    exporter = GitLabCodeQualityExporter()
    exporter.write_gitlab_report([sample_diag], out_file)

    assert out_file.exists()
    content = json.loads(out_file.read_text(encoding="utf-8"))
    assert isinstance(content, list)
    assert len(content) == 1
    assert content[0]["severity"] == "major"
    assert content[0]["location"]["path"] == "vulnerable/early_return_leak.py"


def test_jenkins_ci_exporter(sample_diag: Diagnostic, tmp_path: Path):
    out_file = tmp_path / "leakguard-junit.xml"
    exporter = JenkinsJUnitExporter()
    exporter.write_junit_file([sample_diag], out_file)

    assert out_file.exists()
    xml_str = out_file.read_text(encoding="utf-8")
    root = ET.fromstring(xml_str)
    assert root.tag == "testsuite"
    assert root.attrib["failures"] == "1"


def test_bitbucket_ci_exporter(sample_diag: Diagnostic, tmp_path: Path):
    out_file = tmp_path / "leakguard-bitbucket.json"
    exporter = BitbucketCodeInsightsExporter()
    exporter.write_bitbucket_report([sample_diag], out_file)

    assert out_file.exists()
    content = json.loads(out_file.read_text(encoding="utf-8"))
    assert content["reporter"] == "LeakGuard"
    assert content["result"] == "FAILED"
    assert len(content["annotations"]) == 1


def test_sample_repo_reproducible_scan():
    sample_repo = Path("examples/sample_repo")
    assert sample_repo.exists()

    config = LeakGuardConfig(fail_on="error")
    scanner = ProjectScanner(config)

    scan_result1 = scanner.scan_directory(sample_repo)
    scan_result2 = scanner.scan_directory(sample_repo)

    # 1. Reproducibility
    assert len(scan_result1.diagnostics) == len(scan_result2.diagnostics)
    fps1 = sorted([d.fingerprint for d in scan_result1.diagnostics])
    fps2 = sorted([d.fingerprint for d in scan_result2.diagnostics])
    assert fps1 == fps2

    # 2. Check 5 resource lifecycle patterns:
    vars_found = [d.resource_variable for d in scan_result1.diagnostics]
    files_found = [Path(d.file_path).name for d in scan_result1.diagnostics]

    # Vulnerable files detected
    assert "early_return_leak.py" in files_found
    assert "exception_path_leak.py" in files_found

    # Safe files have 0 findings
    assert "with_statement_safe.py" not in files_found
    assert "try_finally_safe.py" not in files_found
    assert "ownership_transfer_safe.py" not in files_found
