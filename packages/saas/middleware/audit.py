import json
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session

from packages.saas.db.models import AuditEvent


def log_audit_event(
    db: Session,
    org_id: str,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=json.dumps(details or {}),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
