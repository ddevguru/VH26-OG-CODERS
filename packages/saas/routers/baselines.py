import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Baseline, Suppression, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.baseline import (
    BaselineCreate,
    BaselineResponse,
    SuppressionCreate,
    SuppressionResponse,
)
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/baselines", tags=["Baselines & Suppressions"])


@router.get("", response_model=List[BaselineResponse])
def list_baselines(
    repository_id: Optional[str] = None,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(Baseline).filter(Baseline.org_id == ctx.org_id)
    if repository_id:
        query = query.filter(Baseline.repo_id == repository_id)

    baselines = query.all()
    res = []
    for b in baselines:
        fps = json.loads(b.fingerprints_json) if b.fingerprints_json else []
        res.append(
            BaselineResponse(
                id=b.id,
                org_id=b.org_id,
                repo_id=b.repo_id,
                name=b.name,
                fingerprints=fps,
                created_at=b.created_at,
            )
        )
    return res


@router.post("", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED)
def create_baseline(
    req: BaselineCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    b = Baseline(
        org_id=ctx.org_id,
        repo_id=req.repository_id,
        name=req.name,
        fingerprints_json=json.dumps(req.fingerprints),
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_baseline", resource_type="Baseline", resource_id=b.id)
    return BaselineResponse(
        id=b.id,
        org_id=b.org_id,
        repo_id=b.repo_id,
        name=b.name,
        fingerprints=req.fingerprints,
        created_at=b.created_at,
    )


@router.get("/suppressions", response_model=List[SuppressionResponse])
def list_suppressions(
    repository_id: Optional[str] = None,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(Suppression).filter(Suppression.org_id == ctx.org_id)
    if repository_id:
        query = query.filter(Suppression.repo_id == repository_id)

    suppressions = query.all()
    return [
        SuppressionResponse(
            id=s.id,
            org_id=s.org_id,
            repo_id=s.repo_id,
            finding_fingerprint=s.finding_fingerprint,
            reason=s.reason,
            suppressed_by_user_id=s.suppressed_by_user_id,
            created_at=s.created_at,
        )
        for s in suppressions
    ]


@router.post("/suppressions", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
def create_suppression(
    req: SuppressionCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    s = Suppression(
        org_id=ctx.org_id,
        repo_id=req.repository_id,
        finding_fingerprint=req.finding_fingerprint,
        reason=req.reason,
        suppressed_by_user_id=ctx.user.id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_suppression", resource_type="Suppression", resource_id=s.id)
    return SuppressionResponse(
        id=s.id,
        org_id=s.org_id,
        repo_id=s.repo_id,
        finding_fingerprint=s.finding_fingerprint,
        reason=s.reason,
        suppressed_by_user_id=s.suppressed_by_user_id,
        created_at=s.created_at,
    )
