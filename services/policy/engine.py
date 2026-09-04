from typing import List, Union, Optional
from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Severity, Confidence, Policy, PolicyEvaluationResult, ScanResult


class PolicyEngine:
    """Evaluates scan findings against security policy thresholds to determine CI status."""

    SEVERITY_ORDER = {
        Severity.INFO: 1,
        Severity.WARNING: 2,
        Severity.ERROR: 3,
        Severity.CRITICAL: 4,
    }

    CONFIDENCE_NUMERIC = {
        Confidence.LOW: 0.3,
        Confidence.MEDIUM: 0.6,
        Confidence.HIGH: 0.85,
    }

    FAIL_ON_MAP = {
        "info": 1,
        "low": 1,
        "warning": 2,
        "medium": 2,
        "error": 3,
        "high": 3,
        "critical": 4,
        "none": 999,
    }

    def __init__(self, config_or_policy: Optional[Union[LeakGuardConfig, Policy]] = None) -> None:
        if isinstance(config_or_policy, Policy):
            self.policy = config_or_policy
        elif isinstance(config_or_policy, LeakGuardConfig):
            fail_str = config_or_policy.fail_on.lower()
            conf_val = self.CONFIDENCE_NUMERIC.get(config_or_policy.min_confidence, 0.3)
            self.policy = Policy(
                fail_on=fail_str,
                fail_on_severity=config_or_policy.fail_on_severity,
                confidence_threshold=conf_val,
            )
        else:
            self.policy = Policy()

    def evaluate(self, target: Union[ScanResult, List[Diagnostic]]) -> PolicyEvaluationResult:
        diagnostics = target.diagnostics if isinstance(target, ScanResult) else target

        if self.policy.fail_on.lower() == "none":
            return PolicyEvaluationResult(passed=True, blocking_findings=[], suppressed_findings=diagnostics, reasons=["Policy set to 'none' - CI pass guaranteed."])

        fail_level = self.FAIL_ON_MAP.get(self.policy.fail_on.lower(), self.SEVERITY_ORDER.get(self.policy.fail_on_severity, 3))
        conf_min = self.policy.confidence_threshold

        blocking: List[Diagnostic] = []
        suppressed: List[Diagnostic] = []

        for diag in diagnostics:
            diag_sev_level = self.SEVERITY_ORDER.get(diag.severity, 3)
            diag_conf_val = self.CONFIDENCE_NUMERIC.get(diag.confidence, 0.6)

            if diag_sev_level >= fail_level and diag_conf_val >= conf_min:
                blocking.append(diag)
            else:
                suppressed.append(diag)

        reasons: List[str] = []
        passed = True

        if len(blocking) > self.policy.max_allowed_leaks:
            passed = False
            reasons.append(f"Found {len(blocking)} blocking findings exceeding maximum allowed leaks limit ({self.policy.max_allowed_leaks}).")
            reasons.append(f"Configured policy threshold: fail_on='{self.policy.fail_on}', confidence_threshold={self.policy.confidence_threshold}.")

        return PolicyEvaluationResult(
            passed=passed,
            blocking_findings=blocking,
            suppressed_findings=suppressed,
            reasons=reasons,
        )

    def should_fail_ci(self, diagnostics: List[Diagnostic]) -> bool:
        res = self.evaluate(diagnostics)
        return not res.passed
