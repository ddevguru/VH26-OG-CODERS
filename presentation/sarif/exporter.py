import json
from pathlib import Path
from typing import List, Dict, Any, Union

from core.common.models import Diagnostic, Classification, Severity, ScanResult


class SarifExporter:
    """Exports LeakGuard diagnostics into OASIS SARIF 2.1.0 format with codeFlows."""

    def to_sarif_dict(self, target: Union[ScanResult, List[Diagnostic]]) -> Dict[str, Any]:
        diagnostics = target.diagnostics if isinstance(target, ScanResult) else target
        results: List[Dict[str, Any]] = []


        for diag in diagnostics:
            level = "error" if diag.severity in (Severity.ERROR, Severity.CRITICAL) else "warning"

            # Build physical location
            loc_dict: Dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {"uri": diag.file_path.replace("\\", "/")},
                    "region": {
                        "startLine": diag.location.start.line,
                        "startColumn": diag.location.start.column,
                        "endLine": diag.location.end.line,
                        "endColumn": diag.location.end.column,
                    },
                }
            }

            # Build codeFlows for execution path step trace
            thread_flow_locations: List[Dict[str, Any]] = []
            for step in diag.execution_path:
                thread_flow_locations.append({
                    "location": {
                        "physicalLocation": {
                            "artifactLocation": {"uri": diag.file_path.replace("\\", "/")},
                            "region": {
                                "startLine": step.location.start.line,
                                "startColumn": step.location.start.column,
                                "endLine": step.location.end.line,
                                "endColumn": step.location.end.column,
                            },
                        },
                        "message": {"text": f"Step {step.step_number}: {step.description}"},
                    }
                })

            code_flows = []
            if thread_flow_locations:
                code_flows.append({"threadFlows": [{"locations": thread_flow_locations}]})

            results.append({
                "ruleId": diag.rule_id,
                "level": level,
                "message": {"text": f"{diag.classification.value}: {diag.reason}"},
                "locations": [loc_dict],
                "codeFlows": code_flows,
                "properties": {
                    "classification": diag.classification.value,
                    "confidence": diag.confidence.value,
                    "findingId": diag.finding_id,
                    "resourceType": diag.resource_type,
                    "resourceVariable": diag.resource_variable,
                },
            })

        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "LeakGuard",
                            "semanticVersion": "0.1.0",
                            "informationUri": "https://github.com/leakguard/leakguard",
                            "rules": [
                                {
                                    "id": "RULE_LEAK_001",
                                    "name": "ResourceLeak",
                                    "shortDescription": {"text": "Resource Leak Detected"},
                                    "fullDescription": {"text": "AST and Control-Flow based Static Resource Lifetime Analysis for Java."},
                                }
                            ],
                        }
                    },
                    "results": results,
                }
            ],
        }

    def write_sarif_file(self, target: Union[ScanResult, List[Diagnostic]], output_path: Union[str, Path]) -> None:
        sarif_dict = self.to_sarif_dict(target)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sarif_dict, indent=2), encoding="utf-8")

