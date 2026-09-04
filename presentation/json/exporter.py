import json
from pathlib import Path
from typing import List, Dict, Any, Union

from core.common.models import Diagnostic, ScanResult


class JsonExporter:
    """Exports LeakGuard diagnostics and scan results into structured JSON files."""

    def to_json_dict(self, target: Union[ScanResult, List[Diagnostic]]) -> Dict[str, Any]:
        if isinstance(target, ScanResult):
            return {
                "tool": "LeakGuard",
                "version": "0.1.0",
                "status": target.status,
                "finding_count": len(target.diagnostics),
                "baseline_suppressed_count": target.baseline_suppressed_count,
                "statistics": target.statistics.model_dump(mode="json"),
                "findings": [
                    {
                        **diag.model_dump(mode="json"),
                        "fingerprint": diag.fingerprint,
                    }
                    for diag in target.diagnostics
                ],
            }
        else:
            return {
                "tool": "LeakGuard",
                "version": "0.1.0",
                "finding_count": len(target),
                "findings": [
                    {
                        **diag.model_dump(mode="json"),
                        "fingerprint": diag.fingerprint,
                    }
                    for diag in target
                ],
            }

    def write_json_file(self, target: Union[ScanResult, List[Diagnostic]], output_path: Union[str, Path]) -> None:
        json_dict = self.to_json_dict(target)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json_dict, indent=2), encoding="utf-8")

