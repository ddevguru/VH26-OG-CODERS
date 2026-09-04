import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union, Optional

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification, Severity, ScanResult
from services.scan.scanner import ProjectScanner
from services.policy.engine import PolicyEngine
from presentation.sarif.exporter import SarifExporter


class JenkinsJUnitExporter:
    """Exports LeakGuard diagnostics into JUnit XML report format for Jenkins JUnit plugin."""

    def to_junit_xml(self, target: Union[ScanResult, List[Diagnostic]]) -> str:
        diagnostics = target.diagnostics if isinstance(target, ScanResult) else target

        testsuite = ET.Element("testsuite", {
            "name": "LeakGuard.ResourceLifetimeAnalysis",
            "tests": str(max(len(diagnostics), 1)),
            "failures": str(len(diagnostics)),
            "errors": "0",
            "skipped": "0",
        })

        if not diagnostics:
            testcase = ET.SubElement(testsuite, "testcase", {
                "classname": "LeakGuard.CleanScan",
                "name": "NoResourceLeaksDetected",
                "time": "0.00",
            })
        else:
            for diag in diagnostics:
                testcase = ET.SubElement(testsuite, "testcase", {
                    "classname": f"LeakGuard.{diag.resource_type}",
                    "name": f"{diag.file_path}:{diag.location.start.line}:{diag.resource_variable or 'res'}",
                    "time": "0.00",
                })
                failure = ET.SubElement(testcase, "failure", {
                    "message": f"{diag.classification.value}: {diag.reason}",
                    "type": diag.severity.value,
                })
                failure.text = f"File: {diag.file_path}:{diag.location.start.line}\nResource: {diag.resource_variable} ({diag.resource_type})\nReason: {diag.reason}"

        return ET.tostring(testsuite, encoding="unicode")

    def write_junit_file(self, target: Union[ScanResult, List[Diagnostic]], output_path: Union[str, Path] = "leakguard-junit.xml") -> Path:
        xml_str = self.to_junit_xml(target)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(xml_str, encoding="utf-8")
        return out_p


def run_jenkins_ci(target_path: Union[str, Path] = ".", sarif_file: str = "leakguard-results.sarif", junit_file: str = "leakguard-junit.xml", fail_on: str = "error") -> int:
    config = LeakGuardConfig(fail_on=fail_on, report_file=sarif_file)
    scanner = ProjectScanner(config)
    scan_result = scanner.scan_directory(target_path)

    SarifExporter().write_sarif_file(scan_result, sarif_file)
    JenkinsJUnitExporter().write_junit_file(scan_result, junit_file)

    policy_engine = PolicyEngine(config)
    policy_res = policy_engine.evaluate(scan_result)

    return 0 if policy_res.passed else 1
