from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from core.common.models import Diagnostic, Classification, Severity, Confidence, Span, SourceLocation
from services.firewall.engine import FirewallEngine, FirewallPolicy, FirewallResult
from services.diff.engine import PRDiffEngine, PRDiffResult

router = APIRouter(prefix="/api/v1", tags=["Firewall & PR Diff"])


class EvaluateFirewallRequest(BaseModel):
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    policy_override: Optional[Dict[str, str]] = None


class ComparePRDiffRequest(BaseModel):
    pr_number: Optional[str] = "42"
    before_diagnostics: List[Diagnostic] = Field(default_factory=list)
    after_diagnostics: List[Diagnostic] = Field(default_factory=list)


@router.post("/firewall/evaluate", response_model=Dict[str, Any])
def evaluate_firewall(
    req: EvaluateFirewallRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Evaluates scan diagnostics against developer firewall policies."""
    engine = FirewallEngine(req.policy_override)
    res = engine.evaluate(req.diagnostics)
    return res.model_dump()


@router.post("/diff/compare", response_model=Dict[str, Any])
def compare_pr_diff(
    req: ComparePRDiffRequest,
    auth: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
):
    """Compares Before (base commit) vs After (PR commit) resource leaks."""
    engine = PRDiffEngine()
    res = engine.compare(before=req.before_diagnostics, after=req.after_diagnostics, pr_number=req.pr_number)
    return res.model_dump()
