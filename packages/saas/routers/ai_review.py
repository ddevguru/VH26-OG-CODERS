import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import (
    User,
    Scan,
    RoleEnum,
    Finding as DBFinding,
    AIReview as DBAIReview,
    AIAgentActivity as DBAIAgentActivity,
    AIFixVerification as DBAIFixVerification,
)
from packages.saas.auth.rbac import require_role, AuthContext
from core.common.models import Diagnostic, Classification, Span, SourceLocation
from services.ai.models import ReviewMode
from services.ai.orchestrator import AIOrchestrator

router = APIRouter(prefix="/ai", tags=["AI Review & Multi-Agent"])


class ReviewRequest(BaseModel):
    scan_id: Optional[str] = None
    target_path: Optional[str] = "."
    source_code: Optional[str] = ""
    review_mode: ReviewMode = ReviewMode.DETAILED


class ExplainRequest(BaseModel):
    finding_id: str
    rule_id: str = "RULE_LEAK_001"
    file_path: str = "module.py"
    line_number: int = 1
    resource_type: str = "FILE"
    resource_variable: str = "handle"
    source_code: Optional[str] = ""


class FixRequest(BaseModel):
    finding_id: str
    rule_id: str = "RULE_LEAK_001"
    file_path: str = "module.py"
    line_number: int = 1
    resource_type: str = "FILE"
    resource_variable: str = "handle"
    source_code: str


@router.post("/review")
def create_ai_review(
    req: ReviewRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Executes multi-agent AI Code Review for a scan or source code snippet."""
    user_id = auth.user.id if auth.user else "user_default"
    org_id = auth.org_id if hasattr(auth, "org_id") else "org_default"
    orchestrator = AIOrchestrator(user_id=user_id, org_id=org_id)

    diagnostics: List[Diagnostic] = []
    if req.scan_id:
        findings = db.query(DBFinding).filter(DBFinding.scan_id == req.scan_id).all()
        for f in findings:
            span = Span(start=SourceLocation(line=f.line_number, column=1), end=SourceLocation(line=f.line_number, column=10))
            diagnostics.append(
                Diagnostic(
                    finding_id=f.id,
                    rule_id=f.rule_id,
                    message=f.title,
                    classification=Classification(f.classification) if f.classification in Classification._value2member_map_ else Classification.DEFINITE_LEAK,
                    file_path=f.file_path,
                    location=span,
                    resource_type=f.severity,
                    resource_variable=f.title.split("'")[1] if "'" in f.title else "resource",
                    reason=f.description or "Resource unclosed",
                )
            )

    review_res = orchestrator.review(
        diagnostics=diagnostics,
        source_code=req.source_code or "",
        review_mode=req.review_mode,
        target_name=req.target_path or "Project",
    )

    # Persist to DB
    db_review = DBAIReview(
        org_id=org_id,
        user_id=user_id,
        scan_id=req.scan_id,
        target=req.target_path or "Project",
        review_mode=req.review_mode.value,
        overall_status=review_res.overall_status,
        summary=review_res.summary,
        details_json=json.dumps(review_res.model_dump()),
        trace_id=review_res.trace_id,
    )
    db.add(db_review)

    for act in review_res.activity_timeline:
        db_act = DBAIAgentActivity(
            org_id=org_id,
            user_id=user_id,
            scan_id=req.scan_id,
            trace_id=review_res.trace_id,
            agent_name=act.agent_name,
            status=act.status.value if hasattr(act.status, "value") else str(act.status),
            duration_ms=act.duration_ms,
            details=act.details,
        )
        db.add(db_act)

    db.commit()
    db.refresh(db_review)

    return review_res.model_dump()


@router.post("/explain")
def explain_finding(
    req: ExplainRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Generates multi-agent explanation for a single resource finding."""
    user_id = auth.user.id if auth.user else "user_default"
    org_id = auth.org_id if hasattr(auth, "org_id") else "org_default"
    orchestrator = AIOrchestrator(user_id=user_id, org_id=org_id)

    span = Span(start=SourceLocation(line=req.line_number, column=1), end=SourceLocation(line=req.line_number, column=10))
    diag = Diagnostic(
        finding_id=req.finding_id,
        rule_id=req.rule_id,
        message=f"Unclosed {req.resource_type} handle '{req.resource_variable}'",
        classification=Classification.DEFINITE_LEAK,
        file_path=req.file_path,
        location=span,
        resource_type=req.resource_type,
        resource_variable=req.resource_variable,
        reason=f"Resource '{req.resource_variable}' remains unclosed at scope exit.",
    )

    return orchestrator.explain(diag, source_code=req.source_code or "")


@router.post("/fix")
def generate_and_verify_fix(
    req: FixRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
):
    """Generates candidate fix and performs isolated deterministic verification."""
    user_id = auth.user.id if auth.user else "user_default"
    org_id = auth.org_id if hasattr(auth, "org_id") else "org_default"
    orchestrator = AIOrchestrator(user_id=user_id, org_id=org_id)

    span = Span(start=SourceLocation(line=req.line_number, column=1), end=SourceLocation(line=req.line_number, column=10))
    diag = Diagnostic(
        finding_id=req.finding_id,
        rule_id=req.rule_id,
        message=f"Unclosed {req.resource_type} handle '{req.resource_variable}'",
        classification=Classification.DEFINITE_LEAK,
        file_path=req.file_path,
        location=span,
        resource_type=req.resource_type,
        resource_variable=req.resource_variable,
        reason=f"Resource '{req.resource_variable}' remains unclosed at scope exit.",
    )

    result = orchestrator.generate_and_verify_fix(diag, source_code=req.source_code, file_name=req.file_path)

    # Persist verification result in DB
    db_ver = DBAIFixVerification(
        org_id=org_id,
        user_id=user_id,
        finding_id=req.finding_id,
        status=result.get("verification_status", "REJECTED"),
        is_verified=result.get("is_verified", False),
        candidate_patch=result.get("candidate_patch", ""),
        unified_diff=result.get("unified_diff", ""),
        reason=result.get("reason", ""),
    )
    db.add(db_ver)
    db.commit()

    return result


@router.get("/scans/{scan_id}/timeline")
def get_scan_ai_timeline(
    scan_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Retrieves AI Agent activity timeline for a given scan."""
    activities = (
        db.query(DBAIAgentActivity)
        .filter(DBAIAgentActivity.scan_id == scan_id)
        .order_by(DBAIAgentActivity.created_at.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "agent_name": a.agent_name,
            "status": a.status,
            "duration_ms": a.duration_ms,
            "details": a.details,
            "trace_id": a.trace_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]
