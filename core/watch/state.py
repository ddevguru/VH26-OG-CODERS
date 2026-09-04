import time
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification, Severity


def get_finding_key(diag: Diagnostic) -> str:
    """Computes a stable identity string for a diagnostic across scans."""
    func = getattr(diag, "function_name", None) or "global"
    res_var = diag.resource_variable or "resource"
    line = diag.location.start.line if (diag.location and hasattr(diag.location, "start")) else getattr(diag, "line_number", 0)
    rule = diag.rule_id or "LEAK"
    # Relative or basename file path for stability
    file_key = Path(diag.file_path).name if diag.file_path else "unknown"
    return f"{file_key}::{func}::{res_var}::{line}::{rule}"


class SyntaxErrorInfo(BaseModel):
    file_path: Path
    line: int = 1
    column: int = 1
    message: str = "Syntax incomplete"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FindingTransition(BaseModel):
    key: str
    file_path: Path
    function_name: str
    resource_variable: str
    transition_type: str  # "NEW_LEAK", "RESOLVED_LEAK", "CLASSIFICATION_SHIFT"
    old_classification: Optional[str] = None
    new_classification: Optional[str] = None
    diagnostic: Optional[Diagnostic] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)



class WatchState:
    """Thread-safe in-memory watch state maintaining scan metrics, findings map, and live transition diffs."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.status = "● WATCHING"
        self.python_files_count = 0
        self.functions_analyzed_count = 0
        self.resources_tracked_count = 0

        self.safe_count = 0
        self.potential_count = 0
        self.definite_count = 0

        # Current active findings map: key -> Diagnostic
        self.active_findings: Dict[str, Diagnostic] = {}
        # History of all seen finding keys
        self.previous_findings_keys: Set[str] = set()

        self.last_changed_file: Optional[Path] = None
        self.last_scan_timestamp: str = "--:--:--"
        self.last_scan_duration_ms: float = 0.0

        self.last_transitions: List[FindingTransition] = []
        self.syntax_error: Optional[SyntaxErrorInfo] = None

    def record_syntax_error(self, file_path: Path, line: int = 1, message: str = "Syntax incomplete") -> None:
        self.syntax_error = SyntaxErrorInfo(
            file_path=file_path,
            line=line,
            message=message,
        )
        self.last_changed_file = file_path
        self.last_scan_timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    def clear_syntax_error(self) -> None:
        self.syntax_error = None

    def update_scan_results(
        self,
        target_file: Path,
        diagnostics: List[Diagnostic],
        total_files: int,
        total_functions: int,
        total_resources: int,
        duration_ms: float,
    ) -> List[FindingTransition]:
        self.clear_syntax_error()
        self.last_changed_file = target_file
        self.last_scan_duration_ms = duration_ms
        self.last_scan_timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.python_files_count = total_files
        self.functions_analyzed_count = total_functions
        self.resources_tracked_count = total_resources

        # Build map of new scan diagnostics
        new_findings_map: Dict[str, Diagnostic] = {}
        for d in diagnostics:
            key = get_finding_key(d)
            new_findings_map[key] = d

        transitions: List[FindingTransition] = []

        # 1. Detect resolved findings (in active_findings but not in new_findings_map for this file/scope)
        # Note: If target_file is single file, compare findings for that target_file
        target_file_name = target_file.name
        for old_key, old_diag in list(self.active_findings.items()):
            old_file_name = Path(old_diag.file_path).name if old_diag.file_path else ""
            if old_file_name == target_file_name and old_key not in new_findings_map:
                transitions.append(
                    FindingTransition(
                        key=old_key,
                        file_path=Path(old_diag.file_path),
                        function_name=old_diag.function_name or "function",
                        resource_variable=old_diag.resource_variable or "resource",
                        transition_type="RESOLVED_LEAK",
                        old_classification=str(old_diag.classification or "DEFINITE_LEAK"),
                        new_classification="SAFE",
                        diagnostic=old_diag,
                    )
                )

        # 2. Detect new leaks and classification shifts
        for new_key, new_diag in new_findings_map.items():
            func_name = new_diag.function_name or "function"
            res_var = new_diag.resource_variable or "resource"
            new_cls = str(new_diag.classification or Classification.DEFINITE_LEAK.value)

            if new_key not in self.active_findings:
                transitions.append(
                    FindingTransition(
                        key=new_key,
                        file_path=Path(new_diag.file_path),
                        function_name=func_name,
                        resource_variable=res_var,
                        transition_type="NEW_LEAK",
                        old_classification="SAFE",
                        new_classification=new_cls,
                        diagnostic=new_diag,
                    )
                )
            else:
                old_diag = self.active_findings[new_key]
                old_cls = str(old_diag.classification or Classification.DEFINITE_LEAK.value)
                if old_cls != new_cls:
                    transitions.append(
                        FindingTransition(
                            key=new_key,
                            file_path=Path(new_diag.file_path),
                            function_name=func_name,
                            resource_variable=res_var,
                            transition_type="CLASSIFICATION_SHIFT",
                            old_classification=old_cls,
                            new_classification=new_cls,
                            diagnostic=new_diag,
                        )
                    )

        # Update active findings for target_file
        # Remove old findings of target_file
        self.active_findings = {
            k: v for k, v in self.active_findings.items() if Path(v.file_path).name != target_file_name
        }
        # Add new findings
        self.active_findings.update(new_findings_map)

        # Recalculate summary counters
        def_cnt = 0
        pot_cnt = 0

        for d in self.active_findings.values():
            c_str = str(d.classification or "")
            if "DEFINITE" in c_str or d.severity in (Severity.ERROR, Severity.CRITICAL):
                def_cnt += 1
            else:
                pot_cnt += 1

        self.definite_count = def_cnt
        self.potential_count = pot_cnt
        self.safe_count = max(0, self.resources_tracked_count - (def_cnt + pot_cnt))

        self.last_transitions = transitions
        return transitions
