from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime


class MemberRoleUpdate(BaseModel):
    user_id: str
    role: str = Field(..., description="Owner, Admin, Security, Developer, Viewer")


class MemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str
    created_at: datetime
