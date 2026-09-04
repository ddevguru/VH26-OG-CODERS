import yaml
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification, Severity
from core.common.logger import get_logger

logger = get_logger("leakguard.firewall")


class FirewallAction(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    ALLOW = "allow"


class FirewallPolicy(BaseModel):
    definite_leak: FirewallAction = FirewallAction.BLOCK
    potential_leak: FirewallAction = FirewallAction.WARN
    database_leak: FirewallAction = FirewallAction.BLOCK
    socket_leak: FirewallAction = FirewallAction.BLOCK
    file_leak: FirewallAction = FirewallAction.WARN
    subprocess_leak: FirewallAction = FirewallAction.WARN
    http_leak: FirewallAction = FirewallAction.WARN

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def default(cls) -> "FirewallPolicy":
        return cls()


class FirewallResult(BaseModel):
    passed: bool
    status: str  # "PASS" or "BLOCK"
    total_findings: int
    blocked_count: int
    warned_count: int
    allowed_count: int
    blocked_findings: List[Diagnostic] = Field(default_factory=list)
    warned_findings: List[Diagnostic] = Field(default_factory=list)
    allowed_findings: List[Diagnostic] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FirewallEngine:
    """Evaluates scan findings against developer firewall policies for commit/PR gates."""

    def __init__(self, policy_or_config_path: Optional[Union[FirewallPolicy, Dict[str, Any], Path, str]] = None) -> None:
        self.policy = self._parse_policy(policy_or_config_path)

    def _parse_policy(self, input_policy: Optional[Union[FirewallPolicy, Dict[str, Any], Path, str]]) -> FirewallPolicy:
        if isinstance(input_policy, FirewallPolicy):
            return input_policy

        if isinstance(input_policy, dict):
            p_data = input_policy.get("firewall", {}).get("policy", input_policy.get("policy", input_policy))
            return FirewallPolicy(**{k: FirewallAction(v.lower()) for k, v in p_data.items() if hasattr(FirewallPolicy, k)})

        if isinstance(input_policy, (str, Path)):
            c_path = Path(input_policy)
            if c_path.is_file():
                try:
                    content = c_path.read_text(encoding="utf-8")
                    parsed = yaml.safe_load(content) or {}
                    p_data = parsed.get("firewall", {}).get("policy", parsed.get("policy", {}))
                    if p_data:
                        return FirewallPolicy(**{k: FirewallAction(v.lower()) for k, v in p_data.items() if hasattr(FirewallPolicy, k)})
                except Exception as e:
                    logger.warning(f"Failed to load firewall config from {c_path}: {e}")

        # Check default .leakguard.yml if exists
        default_yml = Path(".leakguard.yml")
        if default_yml.is_file():
            try:
                content = default_yml.read_text(encoding="utf-8")
                parsed = yaml.safe_load(content) or {}
                p_data = parsed.get("firewall", {}).get("policy", parsed.get("policy", {}))
                if p_data:
                    return FirewallPolicy(**{k: FirewallAction(v.lower()) for k, v in p_data.items() if hasattr(FirewallPolicy, k)})
            except Exception:
                pass

        return FirewallPolicy.default()

    def evaluate(self, diagnostics: List[Diagnostic]) -> FirewallResult:
        blocked: List[Diagnostic] = []
        warned: List[Diagnostic] = []
        allowed: List[Diagnostic] = []
        reasons: List[str] = []

        for diag in diagnostics:
            action = self._determine_action(diag)
            if action == FirewallAction.BLOCK:
                blocked.append(diag)
            elif action == FirewallAction.WARN:
                warned.append(diag)
            else:
                allowed.append(diag)

        passed = len(blocked) == 0

        if not passed:
            reasons.append(f"Firewall BLOCKED commit/PR: {len(blocked)} findings violated developer firewall blocking rules.")
        else:
            reasons.append(f"Firewall PASSED: 0 blocking findings ({len(warned)} warnings issued).")

        return FirewallResult(
            passed=passed,
            status="PASS" if passed else "BLOCK",
            total_findings=len(diagnostics),
            blocked_count=len(blocked),
            warned_count=len(warned),
            allowed_count=len(allowed),
            blocked_findings=blocked,
            warned_findings=warned,
            allowed_findings=allowed,
            reasons=reasons,
        )

    def _determine_action(self, diag: Diagnostic) -> FirewallAction:
        rule_id = (diag.rule_id or "").upper()
        res_type = str(diag.resource_type or "").upper()

        # Specific resource overrides
        if "DB" in rule_id or "DATABASE" in res_type:
            if self.policy.database_leak == FirewallAction.BLOCK:
                return FirewallAction.BLOCK
        elif "NET" in rule_id or "SOCKET" in res_type:
            if self.policy.socket_leak == FirewallAction.BLOCK:
                return FirewallAction.BLOCK
        elif "FILE" in rule_id or "FILE" in res_type:
            if self.policy.file_leak == FirewallAction.BLOCK:
                return FirewallAction.BLOCK

        # Classification rules
        if diag.classification == Classification.DEFINITE_LEAK:
            return self.policy.definite_leak
        elif diag.classification == Classification.POTENTIAL_LEAK:
            return self.policy.potential_leak

        return FirewallAction.ALLOW
