from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FindingIngestItem(BaseModel):
    rule_id: str
    file_path: str
    line_number: int
    severity: str
    confidence: str
    classification: str
    title: str
    description: Optional[str] = ""
    fingerprint: str


class FindingResponse(BaseModel):
    id: str
    org_id: str
    scan_id: str
    rule_id: str
    file_path: str
    line_number: int
    severity: str
    confidence: str
    classification: str
    title: str
    description: Optional[str] = ""
    fingerprint: str
    status: str
    created_at: datetime


class FindingStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN, RESOLVED, SUPPRESSED")
