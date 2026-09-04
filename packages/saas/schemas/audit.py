from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    org_id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime
