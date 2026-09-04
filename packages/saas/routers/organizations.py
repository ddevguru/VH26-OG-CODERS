from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import re

from packages.saas.db.database import get_db
from packages.saas.db.models import Organization, Team, UserOrgRole, User, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    TeamCreate,
    TeamResponse,
    MemberRoleUpdate,
    MemberResponse,
)
from packages.saas.schemas.common import PaginatedResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/organizations", tags=["Organizations & Teams"])


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    org = db.query(Organization).filter(Organization.id == ctx.org_id).first()
    if not org:
        return []
    return [OrganizationResponse(id=org.id, name=org.name, slug=org.slug, created_at=org.created_at)]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    req: OrganizationCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.OWNER)),
    db: Session = Depends(get_db),
):
    slug = req.slug or slugify(req.name)
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use")

    org = Organization(name=req.name, slug=slug)
    db.add(org)
    db.flush()

    role = UserOrgRole(user_id=ctx.user.id, org_id=org.id, role=RoleEnum.OWNER.value)
    db.add(role)
    db.commit()
    db.refresh(org)

    log_audit_event(db, org_id=org.id, user_id=ctx.user.id, action="create_organization", resource_type="Organization", resource_id=org.id)
    return OrganizationResponse(id=org.id, name=org.name, slug=org.slug, created_at=org.created_at)


@router.get("/teams", response_model=List[TeamResponse])
def list_teams(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    teams = db.query(Team).filter(Team.org_id == ctx.org_id).all()
    return [
        TeamResponse(id=t.id, org_id=t.org_id, name=t.name, description=t.description, created_at=t.created_at)
        for t in teams
    ]


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    req: TeamCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    team = Team(org_id=ctx.org_id, name=req.name, description=req.description)
    db.add(team)
    db.commit()
    db.refresh(team)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_team", resource_type="Team", resource_id=team.id)
    return TeamResponse(id=team.id, org_id=team.org_id, name=team.name, description=team.description, created_at=team.created_at)


@router.get("/members", response_model=PaginatedResponse[MemberResponse])
def list_members(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(UserOrgRole, User).join(User, UserOrgRole.user_id == User.id).filter(UserOrgRole.org_id == ctx.org_id)
    total = query.count()
    results = query.offset(offset).limit(limit).all()

    items = [
        MemberResponse(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=r.role,
            created_at=u.created_at,
        )
        for r, u in results
    ]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.put("/members/role", response_model=MemberResponse)
def update_member_role(
    req: MemberRoleUpdate,
    ctx: AuthContext = Depends(require_role(RoleEnum.OWNER)),
    db: Session = Depends(get_db),
):
    role_record = db.query(UserOrgRole).filter(UserOrgRole.org_id == ctx.org_id, UserOrgRole.user_id == req.user_id).first()
    if not role_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in organization")

    valid_roles = [r.value for r in RoleEnum]
    if req.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role. Must be one of {valid_roles}")

    role_record.role = req.role
    db.commit()

    user = db.query(User).filter(User.id == req.user_id).first()
    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="update_member_role", resource_type="UserOrgRole", resource_id=role_record.id, details={"role": req.role})

    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_record.role,
        created_at=user.created_at,
    )
