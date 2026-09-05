"""PR Risk Scorer — Deterministic-only risk score calculation.

CRITICAL: AI must NEVER modify this score.
The risk score is calculated entirely from LeakGuard's deterministic findings.
"""
from typing import List
from core.common.models import Diagnostic, Classification, ResourceType


# Base weights
CLASSIFICATION_WEIGHTS = {
    Classification.DEFINITE_LEAK: 40,
    Classification.POTENTIAL_LEAK: 20,
    Classification.UNKNOWN: 5,
    Classification.SAFE: 0,
}

RESOURCE_TYPE_WEIGHTS = {
    "DATABASE": 15,
    "SOCKET": 10,
    "HTTP": 8,
    "SUBPROCESS": 8,
    "FILE": 5,
    "LOCK": 10,
    "TEMPFILE": 3,
    "CUSTOM": 5,
}

SEVERITY_LABELS = {
    (0, 1): ("NONE", "⚪"),
    (1, 20): ("LOW", "🟢"),
    (20, 40): ("MEDIUM", "🟡"),
    (40, 60): ("HIGH", "🟠"),
    (60, 80): ("HIGH", "🟠"),
    (80, 101): ("CRITICAL", "🔴"),
}


class PRRiskScorer:
    """Computes a deterministic risk score (0–100) for a PR scan result.

    Factors:
    - Classification severity (DEFINITE > POTENTIAL > UNKNOWN)
    - Resource type (DB connections highest risk)
    - Number of findings
    - Affected paths per finding

    AI cannot modify this score.
    """

    def compute(self, diagnostics: List[Diagnostic]) -> dict:
        """Compute risk score from a list of deterministic findings.

        Returns:
            {
                "score": 87,
                "label": "CRITICAL",
                "emoji": "🔴",
                "definite_count": 2,
                "potential_count": 1,
                "safe_count": 14,
                "factors": [...],
            }
        """
        if not diagnostics:
            return self._result(0, [], 0, 0, 0, 0)

        definite = [d for d in diagnostics if d.classification == Classification.DEFINITE_LEAK]
        potential = [d for d in diagnostics if d.classification == Classification.POTENTIAL_LEAK]
        unknown = [d for d in diagnostics if d.classification == Classification.UNKNOWN]
        safe = [d for d in diagnostics if d.classification == Classification.SAFE]

        base_score = 0
        factors = []

        for d in definite:
            class_w = CLASSIFICATION_WEIGHTS[Classification.DEFINITE_LEAK]
            res_type = str(d.resource_type).upper().replace("RESOURCETYPE.", "")
            res_w = RESOURCE_TYPE_WEIGHTS.get(res_type, 5)
            contribution = class_w + res_w
            base_score += contribution
            factors.append({
                "finding_id": d.finding_id,
                "classification": "DEFINITE_LEAK",
                "resource_type": res_type,
                "contribution": contribution,
                "reason": f"Definite leak (+{class_w}) + {res_type} resource (+{res_w})",
            })

        for d in potential:
            class_w = CLASSIFICATION_WEIGHTS[Classification.POTENTIAL_LEAK]
            res_type = str(d.resource_type).upper().replace("RESOURCETYPE.", "")
            res_w = RESOURCE_TYPE_WEIGHTS.get(res_type, 5) // 2
            contribution = class_w + res_w
            base_score += contribution
            factors.append({
                "finding_id": d.finding_id,
                "classification": "POTENTIAL_LEAK",
                "resource_type": res_type,
                "contribution": contribution,
                "reason": f"Potential leak (+{class_w}) + {res_type} resource (+{res_w})",
            })

        for d in unknown:
            class_w = CLASSIFICATION_WEIGHTS[Classification.UNKNOWN]
            res_type = str(d.resource_type).upper().replace("RESOURCETYPE.", "")
            res_w = RESOURCE_TYPE_WEIGHTS.get(res_type, 5) // 4
            contribution = class_w + res_w
            base_score += contribution
            factors.append({
                "finding_id": d.finding_id,
                "classification": "UNKNOWN",
                "resource_type": res_type,
                "contribution": contribution,
                "reason": f"Unknown ownership (+{class_w}) + {res_type} resource (+{res_w})",
            })

        # Normalize to 0–100
        score = min(100, base_score)

        return self._result(score, factors, len(definite), len(potential), len(safe), len(unknown))

    def _result(
        self,
        score: int,
        factors: list,
        definite: int,
        potential: int,
        safe: int,
        unknown: int = 0,
    ) -> dict:
        label, emoji = "NONE", "⚪"
        for (lo, hi), (lbl, em) in SEVERITY_LABELS.items():
            if lo <= score < hi:
                label, emoji = lbl, em
                break

        return {
            "score": score,
            "label": label,
            "emoji": emoji,
            "definite_count": definite,
            "potential_count": potential,
            "safe_count": safe,
            "unknown_count": unknown,
            "factors": factors,
        }

    def compute_pr_status(self, risk: dict) -> str:
        """Compute PR review status from risk result.

        FAIL   → DEFINITE_LEAK exists
        WARNING → Only POTENTIAL_LEAK
        PASS   → No blocking leaks

        AI cannot change this status.
        """
        if risk["definite_count"] > 0:
            return "FAIL"
        if risk["potential_count"] > 0:
            return "WARNING"
        return "PASS"
