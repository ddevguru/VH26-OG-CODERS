import json
from pathlib import Path
from typing import List, Set, Union, Optional, Dict, Any, Tuple
from core.common.models import Diagnostic, Finding
from core.common.logger import get_logger

logger = get_logger("leakguard.baseline")


class BaselineEngine:
    """Manages creation, loading, and comparison of baseline findings to suppress pre-existing issues."""

    def __init__(self, baseline_file: Optional[Union[str, Path]] = None) -> None:
        self.baseline_file = Path(baseline_file) if baseline_file else None
        self.baseline_fingerprints: Set[str] = set()
        if self.baseline_file and self.baseline_file.is_file():
            self.load_baseline()

    def load_baseline(self) -> None:
        if not self.baseline_file or not self.baseline_file.is_file():
            return
        try:
            content = self.baseline_file.read_text(encoding="utf-8")
            data = json.loads(content)
            fps: Set[str] = set()
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        fps.add(item)
                    elif isinstance(item, dict) and "fingerprint" in item:
                        fps.add(item["fingerprint"])
            elif isinstance(data, dict):
                findings = data.get("findings", [])
                for f in findings:
                    if isinstance(f, str):
                        fps.add(f)
                    elif isinstance(f, dict) and "fingerprint" in f:
                        fps.add(f["fingerprint"])
                if "fingerprints" in data:
                    fps.update(data["fingerprints"])

            self.baseline_fingerprints = fps
            logger.info(f"Loaded {len(fps)} baseline fingerprints from '{self.baseline_file}'.")
        except Exception as e:
            logger.error(f"Failed to load baseline file '{self.baseline_file}': {e}")
            raise ValueError(f"Invalid baseline file: {e}")

    def filter_diagnostics(self, diagnostics: List[Diagnostic]) -> Tuple[List[Diagnostic], List[Diagnostic]]:
        """Splits diagnostics into (new_diagnostics, suppressed_diagnostics)."""
        if not self.baseline_fingerprints:
            return diagnostics, []

        new_diags: List[Diagnostic] = []
        suppressed_diags: List[Diagnostic] = []

        for diag in diagnostics:
            if diag.fingerprint in self.baseline_fingerprints:
                suppressed_diags.append(diag)
            else:
                new_diags.append(diag)

        return new_diags, suppressed_diags

    def create_baseline_data(self, diagnostics: List[Diagnostic]) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "findings_count": len(diagnostics),
            "findings": [
                {
                    "fingerprint": diag.fingerprint,
                    "rule_id": diag.rule_id,
                    "file_path": diag.file_path.replace("\\", "/"),
                    "resource_type": diag.resource_type,
                    "resource_variable": diag.resource_variable,
                    "line": diag.location.start.line,
                    "classification": diag.classification.value,
                }
                for diag in diagnostics
            ],
            "fingerprints": [diag.fingerprint for diag in diagnostics],
        }

    def save_baseline(self, diagnostics: List[Diagnostic], target_path: Optional[Union[str, Path]] = None) -> Path:
        out_path = Path(target_path or self.baseline_file or "leakguard-baseline.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.create_baseline_data(diagnostics)
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Saved baseline with {len(diagnostics)} findings to '{out_path}'.")
        return out_path
