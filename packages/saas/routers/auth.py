from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import re

from packages.saas.db.database import get_db
from packages.saas.db.models import User, Organization, UserOrgRole, Policy, RoleEnum
from packages.saas.auth.security import hash_password, verify_password, create_access_token
from packages.saas.auth.rbac import get_current_user
from packages.saas.schemas.auth import (
    UserSignupRequest,
    UserLoginRequest,
    GoogleAuthRequest,
    TokenResponse,
    UserProfileResponse,
    OrgRoleSummary,
)
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(req: UserSignupRequest, db: Session = Depends(get_db)):
    # Check email uniqueness
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create User
    hashed_pwd = hash_password(req.password)
    user = User(email=req.email, hashed_password=hashed_pwd, full_name=req.full_name)
    db.add(user)
    db.flush()

    # Create Organization
    slug = slugify(req.organization_name)
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=req.organization_name, slug=slug)
    db.add(org)
    db.flush()

    # Create Owner Role
    role = UserOrgRole(user_id=user.id, org_id=org.id, role=RoleEnum.OWNER.value)
    db.add(role)

    # Create Default Policy
    policy = Policy(org_id=org.id, name="Default Security Policy", min_severity="MEDIUM", is_default=True)
    db.add(policy)

    db.commit()
    db.refresh(user)
    db.refresh(org)

    # Audit log
    log_audit_event(db, org_id=org.id, user_id=user.id, action="signup", resource_type="User", resource_id=user.id)

    access_token = create_access_token({"sub": user.id, "org_id": org.id, "role": RoleEnum.OWNER.value})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60,
        user_id=user.id,
        organization_id=org.id,
        role=RoleEnum.OWNER.value,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user_roles = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).all()
    if not user_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no assigned organization")

    primary_role = user_roles[0]
    access_token = create_access_token(
        {"sub": user.id, "org_id": primary_role.org_id, "role": primary_role.role}
    )

    log_audit_event(
        db, org_id=primary_role.org_id, user_id=user.id, action="login", resource_type="User", resource_id=user.id
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60,
        user_id=user.id,
        organization_id=primary_role.org_id,
        role=primary_role.role,
    )


@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()

    if not user:
        # Auto register new user via Google
        hashed_pwd = hash_password(f"google-oauth-pwd-{req.email}")
        user = User(email=req.email, hashed_password=hashed_pwd, full_name=req.full_name or req.email.split("@")[0])
        db.add(user)
        db.flush()

        org_name = req.organization_name or f"{user.full_name}'s Org"
        slug = slugify(org_name)
        base_slug = slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(name=org_name, slug=slug)
        db.add(org)
        db.flush()

        role = UserOrgRole(user_id=user.id, org_id=org.id, role=RoleEnum.OWNER.value)
        db.add(role)

        policy = Policy(org_id=org.id, name="Default Security Policy", min_severity="MEDIUM", is_default=True)
        db.add(policy)

        db.commit()
        db.refresh(user)
        db.refresh(org)
        log_audit_event(db, org_id=org.id, user_id=user.id, action="google_signup", resource_type="User", resource_id=user.id)
    else:
        log_audit_event(db, org_id=user.org_roles[0].org_id if user.org_roles else "", user_id=user.id, action="google_login", resource_type="User", resource_id=user.id)

    user_roles = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).all()
    primary_role = user_roles[0] if user_roles else None
    org_id = primary_role.org_id if primary_role else ""
    user_role = primary_role.role if primary_role else RoleEnum.DEVELOPER.value

    access_token = create_access_token({"sub": user.id, "org_id": org_id, "role": user_role})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 24 * 60,
        user_id=user.id,
        organization_id=org_id,
        role=user_role,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_roles = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).all()
    org_summaries = []
    for r in user_roles:
        org = db.query(Organization).filter(Organization.id == r.org_id).first()
        if org:
            org_summaries.append(
                OrgRoleSummary(organization_id=org.id, organization_name=org.name, role=r.role)
            )

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        organizations=org_summaries,
    )
