from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class FileEventType(str, Enum):
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


class FileEvent(BaseModel):
    path: Path
    event_type: FileEventType
    timestamp: float
    old_path: Optional[Path] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

