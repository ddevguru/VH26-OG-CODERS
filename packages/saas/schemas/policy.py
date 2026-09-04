from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    min_severity: str = "MEDIUM"
    min_confidence: str = "MEDIUM"
    fail_on_leak: bool = True
    is_default: bool = False


class PolicyResponse(BaseModel):
    id: str
    org_id: str
    name: str
    min_severity: str
    min_confidence: str
    fail_on_leak: bool
    is_default: bool
    created_at: datetime
