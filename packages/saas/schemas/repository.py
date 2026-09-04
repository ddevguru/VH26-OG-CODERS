from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    key: str = Field(..., min_length=2, max_length=100)
    team_id: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    org_id: str
    team_id: Optional[str] = None
    name: str
    key: str
    created_at: datetime


class RepositoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    url: Optional[str] = None
    default_branch: str = "main"
    project_id: Optional[str] = None


class RepositoryResponse(BaseModel):
    id: str
    org_id: str
    project_id: Optional[str] = None
    name: str
    url: Optional[str] = None
    default_branch: str
    created_at: datetime
