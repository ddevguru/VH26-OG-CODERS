from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Policy, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.policy import PolicyCreate, PolicyResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/policies", tags=["Security Policies"])


@router.get("", response_model=List[PolicyResponse])
def list_policies(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    policies = db.query(Policy).filter(Policy.org_id == ctx.org_id).all()
    return [
        PolicyResponse(
            id=p.id,
            org_id=p.org_id,
            name=p.name,
            min_severity=p.min_severity,
            min_confidence=p.min_confidence,
            fail_on_leak=p.fail_on_leak,
            is_default=p.is_default,
            created_at=p.created_at,
        )
        for p in policies
    ]


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    req: PolicyCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.SECURITY)),
    db: Session = Depends(get_db),
):
    if req.is_default:
        # Unmark existing default policies
        db.query(Policy).filter(Policy.org_id == ctx.org_id).update({"is_default": False})

    policy = Policy(
        org_id=ctx.org_id,
        name=req.name,
        min_severity=req.min_severity,
        min_confidence=req.min_confidence,
        fail_on_leak=req.fail_on_leak,
        is_default=req.is_default,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_policy", resource_type="Policy", resource_id=policy.id)
    return PolicyResponse(
        id=policy.id,
        org_id=policy.org_id,
        name=policy.name,
        min_severity=policy.min_severity,
        min_confidence=policy.min_confidence,
        fail_on_leak=policy.fail_on_leak,
        is_default=policy.is_default,
        created_at=policy.created_at,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    p = db.query(Policy).filter(Policy.id == policy_id, Policy.org_id == ctx.org_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    return PolicyResponse(
        id=p.id,
        org_id=p.org_id,
        name=p.name,
        min_severity=p.min_severity,
        min_confidence=p.min_confidence,
        fail_on_leak=p.fail_on_leak,
        is_default=p.is_default,
        created_at=p.created_at,
    )
