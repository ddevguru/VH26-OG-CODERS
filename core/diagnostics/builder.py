from typing import List, Optional
from core.common.models import (
    Diagnostic,
    Classification,
    Severity,
    Confidence,
    Span,
    PathStep,
    Finding,
)


class DiagnosticBuilder:
    """Builds structured Diagnostic findings explaining WHAT, WHERE, WHY, PATH, CONFIDENCE, and FIX."""

    @staticmethod
    def build_finding(
        rule_id: str,
        classification: Classification,
        message: str,
        file_path: str,
        location: Span,
        resource_type: str,
        resource_variable: Optional[str],
        execution_path: List[PathStep],
        confidence: Confidence,
        severity: Severity,
        reason: str,
        remediation: str = "Use a context manager ('with' or 'async with') to ensure resource cleanup.",
    ) -> Finding:

        finding_id = f"LEAK_{hash((file_path, location.start.line, resource_variable)) & 0xFFFFFFFF:08x}"
        diag = Diagnostic(
            finding_id=finding_id,
            rule_id=rule_id,
            classification=classification,
            message=message,
            file_path=file_path,
            location=location,
            resource_type=resource_type,
            resource_variable=resource_variable,
            acquisition_location=location,
            execution_path=execution_path,
            confidence=confidence,
            severity=severity,
            reason=reason,
            remediation=remediation,
        )

        return Finding(
            id=finding_id,
            diagnostic=diag,
            fingerprint=f"{rule_id}:{file_path}:{location.start.line}:{resource_variable}",
        )
