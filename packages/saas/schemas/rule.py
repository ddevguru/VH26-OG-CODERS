from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RuleCreate(BaseModel):
    rule_id: str
    name: str
    category: str
    default_severity: str
    default_confidence: str
    description: Optional[str] = None
    is_custom: bool = False


class RuleResponse(BaseModel):
    id: str
    rule_id: str
    name: str
    category: str
    default_severity: str
    default_confidence: str
    description: Optional[str] = None
    is_custom: bool
    created_at: datetime
