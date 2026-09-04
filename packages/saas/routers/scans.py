from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from packages.saas.db.database import get_db
from packages.saas.db.models import Scan, Finding, Repository, RoleEnum
from packages.saas.auth.rbac import require_role, AuthContext
from packages.saas.schemas.scan import (
    ScanIngestRequest,
    ScanResponse,
    ScanDetailResponse,
)
from packages.saas.schemas.finding import FindingResponse
from packages.saas.schemas.common import PaginatedResponse
from packages.saas.middleware.audit import log_audit_event

router = APIRouter(prefix="/scans", tags=["Scans & Ingestion"])


@router.post("", response_model=ScanDetailResponse, status_code=status.HTTP_201_CREATED)
def ingest_scan(
    req: ScanIngestRequest,
    ctx: AuthContext = Depends(require_role(RoleEnum.DEVELOPER)),
    db: Session = Depends(get_db),
):
    # Find or auto-create repo under organization
    repo = (
        db.query(Repository)
        .filter(Repository.org_id == ctx.org_id, Repository.name == req.repository_name)
        .first()
    )
    if not repo:
        repo = Repository(org_id=ctx.org_id, name=req.repository_name, default_branch=req.branch or "main")
        db.add(repo)
        db.flush()

    scan = Scan(
        org_id=ctx.org_id,
        repo_id=repo.id,
        commit_sha=req.commit_sha,
        branch=req.branch,
        status="completed",
        scanned_files_count=req.scanned_files_count,
        duration_seconds=req.duration_seconds,
        policy_passed=req.policy_passed,
        total_findings=len(req.findings),
    )
    db.add(scan)
    db.flush()

    finding_objs = []
    for f in req.findings:
        fo = Finding(
            org_id=ctx.org_id,
            scan_id=scan.id,
            rule_id=f.rule_id,
            file_path=f.file_path,
            line_number=f.line_number,
            severity=f.severity,
            confidence=f.confidence,
            classification=f.classification,
            title=f.title,
            description=f.description,
            fingerprint=f.fingerprint,
            status="OPEN",
        )
        db.add(fo)
        finding_objs.append(fo)

    db.commit()
    db.refresh(scan)

    log_audit_event(
        db,
        org_id=ctx.org_id,
        user_id=ctx.user.id,
        action="ingest_scan",
        resource_type="Scan",
        resource_id=scan.id,
        details={"findings_count": len(req.findings), "repo": req.repository_name},
    )

    finding_responses = [
        FindingResponse(
            id=fo.id,
            org_id=fo.org_id,
            scan_id=fo.scan_id,
            rule_id=fo.rule_id,
            file_path=fo.file_path,
            line_number=fo.line_number,
            severity=fo.severity,
            confidence=fo.confidence,
            classification=fo.classification,
            title=fo.title,
            description=fo.description,
            fingerprint=fo.fingerprint,
            status=fo.status,
            created_at=fo.created_at,
        )
        for fo in finding_objs
    ]

    return ScanDetailResponse(
        id=scan.id,
        org_id=scan.org_id,
        repo_id=scan.repo_id,
        commit_sha=scan.commit_sha,
        branch=scan.branch,
        status=scan.status,
        scanned_files_count=scan.scanned_files_count,
        duration_seconds=scan.duration_seconds,
        policy_passed=scan.policy_passed,
        total_findings=scan.total_findings,
        created_at=scan.created_at,
        findings=finding_responses,
    )


@router.get("", response_model=PaginatedResponse[ScanResponse])
def list_scans(
    repository_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    query = db.query(Scan).filter(Scan.org_id == ctx.org_id)
    if repository_id:
        query = query.filter(Scan.repo_id == repository_id)

    total = query.count()
    scans = query.order_by(Scan.created_at.desc()).offset(offset).limit(limit).all()

    items = [
        ScanResponse(
            id=s.id,
            org_id=s.org_id,
            repo_id=s.repo_id,
            commit_sha=s.commit_sha,
            branch=s.branch,
            status=s.status,
            scanned_files_count=s.scanned_files_count,
            duration_seconds=s.duration_seconds,
            policy_passed=s.policy_passed,
            total_findings=s.total_findings,
            created_at=s.created_at,
        )
        for s in scans
    ]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset, has_more=(offset + limit) < total)


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan(
    scan_id: str,
    ctx: AuthContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.org_id == ctx.org_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    findings = db.query(Finding).filter(Finding.scan_id == scan.id, Finding.org_id == ctx.org_id).all()
    finding_responses = [
        FindingResponse(
            id=fo.id,
            org_id=fo.org_id,
            scan_id=fo.scan_id,
            rule_id=fo.rule_id,
            file_path=fo.file_path,
            line_number=fo.line_number,
            severity=fo.severity,
            confidence=fo.confidence,
            classification=fo.classification,
            title=fo.title,
            description=fo.description,
            fingerprint=fo.fingerprint,
            status=fo.status,
            created_at=fo.created_at,
        )
        for fo in findings
    ]

    return ScanDetailResponse(
        id=scan.id,
        org_id=scan.org_id,
        repo_id=scan.repo_id,
        commit_sha=scan.commit_sha,
        branch=scan.branch,
        status=scan.status,
        scanned_files_count=scan.scanned_files_count,
        duration_seconds=scan.duration_seconds,
        policy_passed=scan.policy_passed,
        total_findings=scan.total_findings,
        created_at=scan.created_at,
        findings=finding_responses,
    )
