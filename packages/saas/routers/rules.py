from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Rule, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.rule import RuleCreate, RuleResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/rules", tags=["Rules Catalog"])


@router.get("", response_model=List[RuleResponse])
def list_rules(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    rules = db.query(Rule).all()
    return [
        RuleResponse(
            id=r.id,
            rule_id=r.rule_id,
            name=r.name,
            category=r.category,
            default_severity=r.default_severity,
            default_confidence=r.default_confidence,
            description=r.description,
            is_custom=r.is_custom,
            created_at=r.created_at,
        )
        for r in rules
    ]


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_custom_rule(
    req: RuleCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    existing = db.query(Rule).filter(Rule.rule_id == req.rule_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rule ID {req.rule_id} already exists")

    rule = Rule(
        rule_id=req.rule_id,
        name=req.name,
        category=req.category,
        default_severity=req.default_severity,
        default_confidence=req.default_confidence,
        description=req.description,
        is_custom=req.is_custom,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_custom_rule", resource_type="Rule", resource_id=rule.id)
    return RuleResponse(
        id=rule.id,
        rule_id=rule.rule_id,
        name=rule.name,
        category=rule.category,
        default_severity=rule.default_severity,
        default_confidence=rule.default_confidence,
        description=rule.description,
        is_custom=rule.is_custom,
        created_at=rule.created_at,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(
    rule_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    r = db.query(Rule).filter((Rule.rule_id == rule_id) | (Rule.id == rule_id)).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    return RuleResponse(
        id=r.id,
        rule_id=r.rule_id,
        name=r.name,
        category=r.category,
        default_severity=r.default_severity,
        default_confidence=r.default_confidence,
        description=r.description,
        is_custom=r.is_custom,
        created_at=r.created_at,
    )
