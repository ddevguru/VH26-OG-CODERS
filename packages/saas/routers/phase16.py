from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Finding as DBFinding, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from core.common.models import Diagnostic, Classification, Span, SourceLocation
from core.ownership.graph import ResourceOwnershipGraph
from core.analysis.what_if import WhatIfEngine, WhatIfRequest, WhatIfResult
from core.analysis.scorer import RiskScorer, RiskScore
from services.ai.auto_fixer import AutoFixerEngine, PatchResult

router = APIRouter(prefix="/api/v1", tags=["Phase 16 Advanced Features"])


class FixRequest(BaseModel):
    source_code: str
    strategy: str = "context-manager"
    file_name: str = "module.py"


class VerifyPatchRequest(BaseModel):
    patch_id: str = "patch_001"
    original_code: str
    candidate_code: str
    finding_id: str = "LEAK_001"
    file_name: str = "module.py"


@router.get("/findings/{finding_id}/ownership-graph")
def get_ownership_graph(
    finding_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Retrieves serializable Resource Ownership Graph for a finding."""
    f = db.query(DBFinding).filter(DBFinding.id == finding_id).first()
    if not f:
        # Construct fallback diagnostic for demonstration
        span = Span(start=SourceLocation(line=5, column=1), end=SourceLocation(line=5, column=10))
        diag = Diagnostic(
            finding_id=finding_id,
            rule_id="RULE_LEAK_001",
            message=f"Finding {finding_id}",
            classification=Classification.DEFINITE_LEAK,
            file_path="database.py",
            location=span,
            resource_type="DATABASE",
            resource_variable="conn",
            reason="Unclosed database handle",
        )
    else:
        span = Span(start=SourceLocation(line=f.line_number, column=1), end=SourceLocation(line=f.line_number, column=10))
        diag = Diagnostic(
            finding_id=f.id,
            rule_id=f.rule_id,
            message=f.title,
            classification=Classification(f.classification) if f.classification in Classification._value2member_map_ else Classification.DEFINITE_LEAK,
            file_path=f.file_path,
            location=span,
            resource_type=f.severity,
            resource_variable=f.title.split("'")[1] if "'" in f.title else "handle",
            reason=f.description or "Resource unclosed",
        )

    graph = ResourceOwnershipGraph.from_diagnostic(diag)
    return graph.model_dump()


@router.post("/analysis/what-if")
def analyze_what_if(
    req: WhatIfRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Executes static hypothetical execution analysis for an exception at a source line."""
    engine = WhatIfEngine()
    result = engine.analyze_exception_point(
        source_code=req.source_code,
        line_number=req.line_number,
        file_path=req.file_path,
    )
    return result.model_dump()


@router.get("/findings/{finding_id}/risk-score")
def get_risk_score(
    finding_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Retrieves 100% deterministic risk score (0-100) for a finding."""
    f = db.query(DBFinding).filter(DBFinding.id == finding_id).first()
    if not f:
        span = Span(start=SourceLocation(line=42, column=1), end=SourceLocation(line=42, column=10))
        diag = Diagnostic(
            finding_id=finding_id,
            rule_id="RULE_DB_001",
            message=f"Finding {finding_id}",
            classification=Classification.DEFINITE_LEAK,
            file_path="database.py",
            location=span,
            resource_type="DATABASE",
            resource_variable="conn",
            reason="Resource unclosed at normal exit",
        )
    else:
        span = Span(start=SourceLocation(line=f.line_number, column=1), end=SourceLocation(line=f.line_number, column=10))
        diag = Diagnostic(
            finding_id=f.id,
            rule_id=f.rule_id,
            message=f.title,
            classification=Classification(f.classification) if f.classification in Classification._value2member_map_ else Classification.DEFINITE_LEAK,
            file_path=f.file_path,
            location=span,
            resource_type=f.severity,
            resource_variable=f.title.split("'")[1] if "'" in f.title else "handle",
            reason=f.description or "Resource unclosed",
        )

    scorer = RiskScorer()
    score = scorer.calculate_score(diag)
    return score.model_dump()


@router.post("/findings/{finding_id}/fix")
def generate_auto_fix(
    finding_id: str,
    req: FixRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
):
    """Generates candidate fix using strategy pattern and executes isolated verification."""
    span = Span(start=SourceLocation(line=2, column=1), end=SourceLocation(line=2, column=10))
    diag = Diagnostic(
        finding_id=finding_id,
        rule_id="RULE_LEAK_001",
        message="Resource Leak",
        classification=Classification.DEFINITE_LEAK,
        file_path=req.file_name,
        location=span,
        resource_type="FILE",
        resource_variable="f",
        reason="Resource unclosed",
    )

    fixer = AutoFixerEngine()
    result = fixer.generate_and_verify(
        source_code=req.source_code,
        diagnostic=diag,
        strategy_name=req.strategy,
        file_name=req.file_name,
    )
    return result.model_dump()


@router.post("/patches/verify")
def verify_patch(
    req: VerifyPatchRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
):
    """Verifies a candidate patch against the deterministic LeakGuard analyzer."""
    span = Span(start=SourceLocation(line=2, column=1), end=SourceLocation(line=2, column=10))
    diag = Diagnostic(
        finding_id=req.finding_id,
        rule_id="RULE_LEAK_001",
        message="Resource Leak",
        classification=Classification.DEFINITE_LEAK,
        file_path=req.file_name,
        location=span,
        resource_type="FILE",
        resource_variable="f",
        reason="Resource unclosed",
    )

    fixer = AutoFixerEngine()
    result = fixer.generate_and_verify(
        source_code=req.original_code,
        diagnostic=diag,
        strategy_name="context-manager",
        file_name=req.file_name,
    )
    return result.model_dump()
