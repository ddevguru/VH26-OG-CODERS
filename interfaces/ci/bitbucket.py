import json
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification, Severity, ScanResult
from services.scan.scanner import ProjectScanner
from services.policy.engine import PolicyEngine


class BitbucketCodeInsightsExporter:
    """Exports LeakGuard diagnostics into Bitbucket Code Insights report JSON schema."""

    def to_bitbucket_report(self, target: Union[ScanResult, List[Diagnostic]]) -> Dict[str, Any]:
        diagnostics = target.diagnostics if isinstance(target, ScanResult) else target

        annotations: List[Dict[str, Any]] = []
        for idx, diag in enumerate(diagnostics, 1):
            severity = "HIGH" if diag.severity in (Severity.ERROR, Severity.CRITICAL) else "MEDIUM"
            annotations.append({
                "external_id": f"LEAK-{idx}-{diag.fingerprint[:8]}",
                "annotation_type": "VULNERABILITY",
                "summary": f"{diag.classification.value}: {diag.reason}",
                "path": diag.file_path.replace("\\", "/"),
                "line": diag.location.start.line,
                "severity": severity,
            })

        return {
            "title": "LeakGuard Static Resource Lifetime Analysis",
            "details": f"Analyzed project resources. Found {len(diagnostics)} findings.",
            "report_type": "SECURITY",
            "reporter": "LeakGuard",
            "result": "FAILED" if any(d.severity in (Severity.ERROR, Severity.CRITICAL) for d in diagnostics) else "PASSED",
            "data": [
                {"label": "Total Findings", "type": "NUMBER", "value": len(diagnostics)},
            ],
            "annotations": annotations,
        }

    def write_bitbucket_report(self, target: Union[ScanResult, List[Diagnostic]], output_path: Union[str, Path] = "leakguard-bitbucket.json") -> Path:
        data = self.to_bitbucket_report(target)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return out_p


def run_bitbucket_ci(target_path: Union[str, Path] = ".", report_file: str = "leakguard-bitbucket.json", fail_on: str = "error") -> int:
    config = LeakGuardConfig(fail_on=fail_on, report_file=report_file)
    scanner = ProjectScanner(config)
    scan_result = scanner.scan_directory(target_path)

    BitbucketCodeInsightsExporter().write_bitbucket_report(scan_result, report_file)

    policy_engine = PolicyEngine(config)
    policy_res = policy_engine.evaluate(scan_result)

    return 0 if policy_res.passed else 1
