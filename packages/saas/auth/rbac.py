from typing import Optional, List
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import User, UserOrgRole, RoleEnum
from packages.saas.auth.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)

ROLE_LEVELS = {
    RoleEnum.OWNER.value: 5,
    RoleEnum.ADMIN.value: 4,
    RoleEnum.SECURITY.value: 3,
    RoleEnum.DEVELOPER.value: 2,
    RoleEnum.VIEWER.value: 1,
}


class AuthContext:
    def __init__(self, user: User, org_id: str, role: str):
        self.user = user
        self.org_id = org_id
        self.role = role


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_auth_context(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthContext:
    # Query user's org roles
    user_roles = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).all()
    if not user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any organization",
        )

    target_org_id = x_organization_id
    if not target_org_id:
        target_org_id = user_roles[0].org_id

    role_record = (
        db.query(UserOrgRole)
        .filter(UserOrgRole.user_id == user.id, UserOrgRole.org_id == target_org_id)
        .first()
    )
    if not role_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to organization {target_org_id}",
        )

    return AuthContext(user=user, org_id=target_org_id, role=role_record.role)


def require_role(min_role: RoleEnum):
    def dependency(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        user_level = ROLE_LEVELS.get(ctx.role, 0)
        required_level = ROLE_LEVELS.get(min_role.value, 99)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {min_role.value}, current role: {ctx.role}",
            )
        return ctx

    return dependency
