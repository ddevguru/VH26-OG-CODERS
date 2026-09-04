from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntegrationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    integration_type: str = Field(..., description="github, gitlab, slack, webhook")
    config: Dict[str, Any] = {}
    is_active: bool = True


class IntegrationResponse(BaseModel):
    id: str
    org_id: str
    name: str
    integration_type: str
    config: Dict[str, Any]  # Masked config
    is_active: bool
    created_at: datetime
