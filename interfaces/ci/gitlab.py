import json
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification, Severity, ScanResult
from services.scan.scanner import ProjectScanner
from services.policy.engine import PolicyEngine


class GitLabCodeQualityExporter:
    """Exports LeakGuard diagnostics into GitLab Code Quality JSON report schema."""

    SEVERITY_MAP = {
        Severity.INFO: "info",
        Severity.WARNING: "minor",
        Severity.ERROR: "major",
        Severity.CRITICAL: "critical",
    }

    def to_gitlab_dict(self, target: Union[ScanResult, List[Diagnostic]]) -> List[Dict[str, Any]]:
        diagnostics = target.diagnostics if isinstance(target, ScanResult) else target
        reports: List[Dict[str, Any]] = []

        for diag in diagnostics:
            gl_sev = self.SEVERITY_MAP.get(diag.severity, "major")
            rel_path = diag.file_path.replace("\\", "/")
            reports.append({
                "description": f"[{diag.classification.value}] {diag.message} - {diag.reason}",
                "fingerprint": diag.fingerprint,
                "severity": gl_sev,
                "location": {
                    "path": rel_path,
                    "lines": {
                        "begin": diag.location.start.line,
                    },
                },
            })

        return reports

    def write_gitlab_report(self, target: Union[ScanResult, List[Diagnostic]], output_path: Union[str, Path] = "gl-code-quality-report.json") -> Path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_gitlab_dict(target)
        out_p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return out_p


def run_gitlab_ci(target_path: Union[str, Path] = ".", report_file: str = "gl-code-quality-report.json", fail_on: str = "error") -> int:
    config = LeakGuardConfig(fail_on=fail_on, report_file=report_file)
    scanner = ProjectScanner(config)
    scan_result = scanner.scan_directory(target_path)

    GitLabCodeQualityExporter().write_gitlab_report(scan_result, report_file)

    policy_engine = PolicyEngine(config)
    policy_res = policy_engine.evaluate(scan_result)

    return 0 if policy_res.passed else 1
