from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class BaselineCreate(BaseModel):
    repository_id: str
    name: str = "default"
    fingerprints: List[str] = []


class BaselineResponse(BaseModel):
    id: str
    org_id: str
    repo_id: str
    name: str
    fingerprints: List[str]
    created_at: datetime


class SuppressionCreate(BaseModel):
    repository_id: str
    finding_fingerprint: str
    reason: Optional[str] = None


class SuppressionResponse(BaseModel):
    id: str
    org_id: str
    repo_id: str
    finding_fingerprint: str
    reason: Optional[str] = None
    suppressed_by_user_id: Optional[str] = None
    created_at: datetime
