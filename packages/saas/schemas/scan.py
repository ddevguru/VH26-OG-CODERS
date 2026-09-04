from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from packages.saas.schemas.finding import FindingIngestItem, FindingResponse


class ScanIngestRequest(BaseModel):
    repository_name: str
    commit_sha: Optional[str] = "HEAD"
    branch: Optional[str] = "main"
    scanned_files_count: int = 0
    duration_seconds: float = 0.0
    policy_passed: bool = True
    findings: List[FindingIngestItem] = []


class ScanResponse(BaseModel):
    id: str
    org_id: str
    repo_id: str
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    status: str
    scanned_files_count: int
    duration_seconds: float
    policy_passed: bool
    total_findings: int
    created_at: datetime


class ScanDetailResponse(ScanResponse):
    findings: List[FindingResponse] = []
