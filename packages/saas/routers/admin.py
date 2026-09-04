from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import User, Organization, Repository, Scan, Finding, UserOrgRole, AuditEvent, RoleEnum
from packages.saas.auth.rbac import get_current_user
from packages.saas.schemas.common import PaginatedResponse

router = APIRouter(prefix="/admin", tags=["Admin Control Plane"])


@router.get("/stats")
def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()
    total_orgs = db.query(Organization).count()
    total_repos = db.query(Repository).count()
    total_scans = db.query(Scan).count()
    total_findings = db.query(Finding).count()
    open_leaks = db.query(Finding).filter(Finding.status == "OPEN").count()

    recent_scans = (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_users": total_users,
        "total_organizations": total_orgs,
        "total_repositories": total_repos,
        "total_scans": total_scans,
        "total_findings": total_findings,
        "open_leaks": open_leaks,
        "recent_scans_count": len(recent_scans),
        "system_status": "healthy",
    }


@router.get("/users")
def get_admin_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    user_list = []
    for u in users:
        roles = db.query(UserOrgRole).filter(UserOrgRole.user_id == u.id).all()
        org_names = []
        primary_role = "User"
        for r in roles:
            org = db.query(Organization).filter(Organization.id == r.org_id).first()
            if org:
                org_names.append(org.name)
            primary_role = r.role

        user_list.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "organizations": org_names,
            "role": primary_role,
        })

    return PaginatedResponse(
        items=user_list,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/scans")
def get_admin_scans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(Scan).count()
    scans = db.query(Scan).order_by(Scan.created_at.desc()).offset(offset).limit(limit).all()

    scan_list = []
    for s in scans:
        repo = db.query(Repository).filter(Repository.id == s.repo_id).first()
        org = db.query(Organization).filter(Organization.id == s.org_id).first()
        scan_list.append({
            "id": s.id,
            "org_name": org.name if org else "Default Org",
            "repository_name": repo.name if repo else "Unknown",
            "commit_sha": s.commit_sha or "HEAD",
            "branch": s.branch or "main",
            "status": s.status,
            "scanned_files_count": s.scanned_files_count,
            "duration_seconds": s.duration_seconds,
            "policy_passed": s.policy_passed,
            "total_findings": s.total_findings,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return PaginatedResponse(
        items=scan_list,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )
