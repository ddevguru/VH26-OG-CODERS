import math
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification, Severity, Confidence, ResourceState


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactor(BaseModel):
    name: str
    weight: float
    score_contribution: float
    description: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RiskProfile(BaseModel):
    category: str
    base_weight: float
    description: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


DEFAULT_PROFILES: Dict[str, RiskProfile] = {
    "DATABASE": RiskProfile(category="database_connection", base_weight=85.0, description="Database connection or cursor handle"),
    "SOCKET": RiskProfile(category="socket", base_weight=80.0, description="Network socket or stream handle"),
    "SUBPROCESS": RiskProfile(category="subprocess", base_weight=75.0, description="Subprocess or process handle"),
    "LOCK": RiskProfile(category="lock", base_weight=70.0, description="Concurrency lock or semaphore"),
    "HTTP": RiskProfile(category="session", base_weight=65.0, description="HTTP client session or response connection"),
    "ASYNC": RiskProfile(category="async_resource", base_weight=65.0, description="Asynchronous resource handle"),
    "CURSOR": RiskProfile(category="cursor", base_weight=60.0, description="Database query cursor"),
    "FILE": RiskProfile(category="file", base_weight=50.0, description="File stream or descriptor"),
    "CUSTOM": RiskProfile(category="custom_resource", base_weight=55.0, description="Custom autocloseable resource"),
}


class RiskScore(BaseModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RiskScorer:
    """100% Deterministic Risk Scoring Engine (0–100 scale).
    
    GUARANTEE: LLMs are NEVER used to generate or modify risk scores.
    The score is calculated deterministically from resource profiles, classification,
    severity, exception path exposure, concurrency, and control-flow complexity.
    """

    def __init__(self, profiles: Optional[Dict[str, RiskProfile]] = None) -> None:
        self.profiles = profiles or DEFAULT_PROFILES

    def calculate_score(self, diagnostic: Diagnostic) -> RiskScore:
        factors: List[RiskFactor] = []

        # 1. Base Resource Profile Contribution (Weight: up to 35%)
        res_type_str = str(diagnostic.resource_type).upper()
        profile_key = "FILE"
        for k in self.profiles:
            if k in res_type_str:
                profile_key = k
                break
        profile = self.profiles.get(profile_key, DEFAULT_PROFILES["FILE"])
        base_contrib = (profile.base_weight / 100.0) * 35.0
        factors.append(
            RiskFactor(
                name="Resource Category",
                weight=35.0,
                score_contribution=round(base_contrib, 2),
                description=f"Base risk for '{profile.category}' profile ({profile.base_weight:.0f}/100)",
            )
        )

        # 2. Classification Certainty (Weight: up to 25%)
        class_score = 25.0 if diagnostic.classification == Classification.DEFINITE_LEAK else 15.0
        factors.append(
            RiskFactor(
                name="Leak Classification Certainty",
                weight=25.0,
                score_contribution=round(class_score, 2),
                description=f"Classification '{diagnostic.classification.value}' certainty weight",
            )
        )

        # 3. Severity Level (Weight: up to 20%)
        sev_map = {
            Severity.CRITICAL: 20.0,
            Severity.ERROR: 16.0,
            Severity.WARNING: 10.0,
            Severity.INFO: 4.0,
        }
        sev_score = sev_map.get(diagnostic.severity, 16.0)
        factors.append(
            RiskFactor(
                name="Diagnostic Severity",
                weight=20.0,
                score_contribution=round(sev_score, 2),
                description=f"Severity level '{diagnostic.severity.value}' weight",
            )
        )

        # 4. Exception Path Exposure (Weight: up to 10%)
        is_exception_exposed = "exception" in diagnostic.reason.lower() or "branch" in diagnostic.reason.lower()
        exc_score = 10.0 if is_exception_exposed else 5.0
        factors.append(
            RiskFactor(
                name="Exception Path Exposure",
                weight=10.0,
                score_contribution=round(exc_score, 2),
                description="Resource leak occurs along exceptional or conditional control-flow branches",
            )
        )

        # 5. Execution Path Complexity & Concurrency (Weight: up to 10%)
        path_len = len(diagnostic.execution_path) if diagnostic.execution_path else 1
        path_score = min(10.0, path_len * 2.5)
        factors.append(
            RiskFactor(
                name="Path Complexity",
                weight=10.0,
                score_contribution=round(path_score, 2),
                description=f"Control-flow path complexity ({path_len} execution step(s))",
            )
        )

        # Compute Total Deterministic Score (Bounded 0 to 100)
        raw_total = sum(f.score_contribution for f in factors)
        final_score = int(round(max(0.0, min(100.0, raw_total))))

        # Determine Level
        if final_score >= 80:
            level = RiskLevel.CRITICAL
        elif final_score >= 60:
            level = RiskLevel.HIGH
        elif final_score >= 30:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        var_name = diagnostic.resource_variable or "handle"
        explanation = (
            f"Deterministic Risk Score: {final_score}/100 [{level.value}]. "
            f"Unclosed {diagnostic.resource_type} handle '{var_name}' evaluated against "
            f"'{profile.category}' profile and control-flow severity factors."
        )

        return RiskScore(
            score=final_score,
            level=level,
            factors=factors,
            explanation=explanation,
        )
