import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Integration, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.integration import IntegrationCreate, IntegrationResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def mask_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    masked = {}
    secret_keywords = ["secret", "token", "key", "password", "auth", "url"]
    for k, v in config.items():
        if any(keyword in k.lower() for keyword in secret_keywords) and isinstance(v, str):
            if len(v) > 8:
                masked[k] = f"{v[:4]}...{v[-4:]}"
            else:
                masked[k] = "********"
        else:
            masked[k] = v
    return masked


@router.get("", response_model=List[IntegrationResponse])
def list_integrations(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    integrations = db.query(Integration).filter(Integration.org_id == ctx.org_id).all()
    res = []
    for i in integrations:
        cfg = json.loads(i.config_json) if i.config_json else {}
        res.append(
            IntegrationResponse(
                id=i.id,
                org_id=i.org_id,
                name=i.name,
                integration_type=i.integration_type,
                config=mask_secrets(cfg),
                is_active=i.is_active,
                created_at=i.created_at,
            )
        )
    return res


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    req: IntegrationCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    valid_types = ["github", "gitlab", "jenkins", "slack", "webhook"]
    if req.integration_type.lower() not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration_type. Must be one of {valid_types}",
        )

    integration = Integration(
        org_id=ctx.org_id,
        name=req.name,
        integration_type=req.integration_type.lower(),
        config_json=json.dumps(req.config),
        is_active=req.is_active,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_integration", resource_type="Integration", resource_id=integration.id)

    return IntegrationResponse(
        id=integration.id,
        org_id=integration.org_id,
        name=integration.name,
        integration_type=integration.integration_type,
        config=mask_secrets(req.config),
        is_active=integration.is_active,
        created_at=integration.created_at,
    )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    integration_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    integration = db.query(Integration).filter(Integration.id == integration_id, Integration.org_id == ctx.org_id).first()
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    db.delete(integration)
    db.commit()

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="delete_integration", resource_type="Integration", resource_id=integration_id)
    return None
