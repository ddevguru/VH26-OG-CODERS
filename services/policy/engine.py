from typing import List
from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Severity


class PolicyEngine:
    """Evaluates scan findings against security policy thresholds to determine CI status."""

    SEVERITY_ORDER = {
        Severity.INFO: 1,
        Severity.WARNING: 2,
        Severity.ERROR: 3,
        Severity.CRITICAL: 4,
    }

    def __init__(self, config: LeakGuardConfig) -> None:
        self.config = config

    def should_fail_ci(self, diagnostics: List[Diagnostic]) -> bool:
        threshold_level = self.SEVERITY_ORDER.get(self.config.fail_on_severity, 3)

        for diag in diagnostics:
            diag_level = self.SEVERITY_ORDER.get(diag.severity, 3)
            if diag_level >= threshold_level:
                return True

        return False
