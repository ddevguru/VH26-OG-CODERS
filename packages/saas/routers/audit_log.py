import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import AuditEvent, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.audit import AuditEventResponse
from packages.saas.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get("", response_model=PaginatedResponse[AuditEventResponse])
def get_audit_log(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_role(RoleEnum.SECURITY)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditEvent).filter(AuditEvent.org_id == ctx.org_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if user_id:
        query = query.filter(AuditEvent.user_id == user_id)

    total = query.count()
    events = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for e in events:
        details = json.loads(e.details_json) if e.details_json else {}
        items.append(
            AuditEventResponse(
                id=e.id,
                org_id=e.org_id,
                user_id=e.user_id,
                action=e.action,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                details=details,
                created_at=e.created_at,
            )
        )

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)
