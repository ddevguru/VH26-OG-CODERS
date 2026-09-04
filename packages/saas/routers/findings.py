from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Finding, RoleEnum, FindingStatusEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.finding import FindingResponse, FindingStatusUpdate
from packages.saas.schemas.common import PaginatedResponse
from packages.saas.middleware.audit import log_audit_event

from services.ai.remediator import AIRemediator
from services.ai.validator import PatchValidator
from core.common.models import Diagnostic, Span, SourceLocation, Severity, Confidence, Classification

router = APIRouter(prefix="/findings", tags=["Findings & AI Remediation"])


class ApplyPatchRequest(BaseModel):
    approved: bool = False
    patch_code: Optional[str] = None


@router.get("", response_model=PaginatedResponse[FindingResponse])
def list_findings(
    scan_id: Optional[str] = None,
    severity: Optional[str] = None,
    finding_status: Optional[str] = Query(None, alias="status"),
    rule_id: Optional[str] = None,
    fingerprint: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(Finding).filter(Finding.org_id == ctx.org_id)
    if scan_id:
        query = query.filter(Finding.scan_id == scan_id)
    if severity:
        query = query.filter(Finding.severity == severity.upper())
    if finding_status:
        query = query.filter(Finding.status == finding_status.upper())
    if rule_id:
        query = query.filter(Finding.rule_id == rule_id)
    if fingerprint:
        query = query.filter(Finding.fingerprint == fingerprint)

    total = query.count()
    findings = query.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        FindingResponse(
            id=f.id,
            org_id=f.org_id,
            scan_id=f.scan_id,
            rule_id=f.rule_id,
            file_path=f.file_path,
            line_number=f.line_number,
            severity=f.severity,
            confidence=f.confidence,
            classification=f.classification,
            title=f.title,
            description=f.description,
            fingerprint=f.fingerprint,
            status=f.status,
            created_at=f.created_at,
        )
        for f in findings
    ]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.org_id == ctx.org_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    return FindingResponse(
        id=f.id,
        org_id=f.org_id,
        scan_id=f.scan_id,
        rule_id=f.rule_id,
        file_path=f.file_path,
        line_number=f.line_number,
        severity=f.severity,
        confidence=f.confidence,
        classification=f.classification,
        title=f.title,
        description=f.description,
        fingerprint=f.fingerprint,
        status=f.status,
        created_at=f.created_at,
    )


@router.patch("/{finding_id}/status", response_model=FindingResponse)
def update_finding_status(
    finding_id: str,
    req: FindingStatusUpdate,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.org_id == ctx.org_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    valid_statuses = [s.value for s in FindingStatusEnum]
    if req.status.upper() not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Must be one of {valid_statuses}")

    f.status = req.status.upper()
    db.commit()

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="update_finding_status", resource_type="Finding", resource_id=f.id, details={"status": f.status})

    return FindingResponse(
        id=f.id,
        org_id=f.org_id,
        scan_id=f.scan_id,
        rule_id=f.rule_id,
        file_path=f.file_path,
        line_number=f.line_number,
        severity=f.severity,
        confidence=f.confidence,
        classification=f.classification,
        title=f.title,
        description=f.description,
        fingerprint=f.fingerprint,
        status=f.status,
        created_at=f.created_at,
    )


@router.post("/{finding_id}/remediate")
def remediate_finding(
    finding_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.org_id == ctx.org_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    # Build mock Diagnostic representation for remediator & validator
    loc = Span(start=SourceLocation(line=f.line_number, column=1), end=SourceLocation(line=f.line_number, column=20))
    diag = Diagnostic(
        finding_id=f.id,
        rule_id=f.rule_id,
        message=f.title,
        file_path=f.file_path,
        location=loc,
        resource_type=f.rule_id.split("-")[1] if "-" in f.rule_id else "RESOURCE",
        severity=Severity.ERROR,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK if f.classification == "DEFINITE_LEAK" else Classification.POTENTIAL_LEAK,
        reason=f.title,
        remediation=f.description or "Use context manager to enclose resource handle.",
    )

    sample_snippet = f"def handle_resource():\n    f = open('{f.file_path}')\n    return f.read()\n"

    remediator = AIRemediator()
    rem_result = remediator.generate_candidate_patch(sample_snippet, diag)

    validator = PatchValidator()
    val_report = validator.validate_patch(sample_snippet, rem_result.candidate_code, diag, file_name=f.file_path.split("/")[-1])

    log_audit_event(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="ai_remediate_finding",
        resource_type="Finding",
        resource_id=f.id,
        details={"is_valid": val_report.is_valid, "provider": rem_result.provider},
    )

    return {
        "finding_id": f.id,
        "explanation": rem_result.explanation,
        "suggested_fix": rem_result.suggested_fix,
        "candidate_code": rem_result.candidate_code,
        "is_ai_generated": rem_result.is_ai_generated,
        "provider": rem_result.provider,
        "validation_report": val_report.model_dump(),
    }


@router.post("/{finding_id}/apply-patch", response_model=FindingResponse)
def apply_patch(
    finding_id: str,
    req: ApplyPatchRequest,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    f = db.query(Finding).filter(Finding.id == finding_id, Finding.org_id == ctx.org_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if not req.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Human approval is explicitly required to apply an AI-assisted patch.",
        )

    f.status = FindingStatusEnum.RESOLVED.value
    db.commit()

    log_audit_event(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="apply_ai_patch",
        resource_type="Finding",
        resource_id=f.id,
        details={"approved": True, "status": f.status},
    )

    return FindingResponse(
        id=f.id,
        org_id=f.org_id,
        scan_id=f.scan_id,
        rule_id=f.rule_id,
        file_path=f.file_path,
        line_number=f.line_number,
        severity=f.severity,
        confidence=f.confidence,
        classification=f.classification,
        title=f.title,
        description=f.description,
        fingerprint=f.fingerprint,
        status=f.status,
        created_at=f.created_at,
    )
