from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Repository, Project, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    ProjectCreate,
    ProjectResponse,
)
from packages.saas.schemas.common import PaginatedResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/repositories", tags=["Repositories & Projects"])


@router.get("", response_model=PaginatedResponse[RepositoryResponse])
def list_repositories(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(Repository).filter(Repository.org_id == ctx.org_id)
    total = query.count()
    repos = query.offset(offset).limit(limit).all()

    items = [
        RepositoryResponse(
            id=r.id,
            org_id=r.org_id,
            project_id=r.project_id,
            name=r.name,
            url=r.url,
            default_branch=r.default_branch,
            created_at=r.created_at,
        )
        for r in repos
    ]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    req: RepositoryCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    repo = Repository(
        org_id=ctx.org_id,
        project_id=req.project_id,
        name=req.name,
        url=req.url,
        default_branch=req.default_branch,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_repository", resource_type="Repository", resource_id=repo.id)
    return RepositoryResponse(
        id=repo.id,
        org_id=repo.org_id,
        project_id=repo.project_id,
        name=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
        created_at=repo.created_at,
    )


@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)), db: Session = Depends(get_db)
):
    projects = db.query(Project).filter(Project.org_id == ctx.org_id).all()
    return [
        ProjectResponse(
            id=p.id,
            org_id=p.org_id,
            team_id=p.team_id,
            name=p.name,
            key=p.key,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    ctx: AuthContext = Depends(require_role(RoleEnum.ADMIN)),
    db: Session = Depends(get_db),
):
    project = Project(
        org_id=ctx.org_id,
        team_id=req.team_id,
        name=req.name,
        key=req.key,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    log_audit_event(db, org_id=ctx.org_id, user_id=ctx.user.id, action="create_project", resource_type="Project", resource_id=project.id)
    return ProjectResponse(
        id=project.id,
        org_id=project.org_id,
        team_id=project.team_id,
        name=project.name,
        key=project.key,
        created_at=project.created_at,
    )
