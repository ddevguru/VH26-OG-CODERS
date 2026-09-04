from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResourceState(str, Enum):
    UNACQUIRED = "UNACQUIRED"
    OPEN_MUST_CLOSE = "OPEN_MUST_CLOSE"
    CLOSED = "CLOSED"
    TRANSFERRED = "TRANSFERRED"
    MAYBE_LEAKED = "MAYBE_LEAKED"
    LEAKED = "LEAKED"


class SourceLocation(BaseModel):
    line: int = Field(..., description="1-indexed line number")
    column: int = Field(..., description="1-indexed column number")
    byte_offset: Optional[int] = Field(None, description="0-indexed byte offset in file")

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


class Span(BaseModel):
    start: SourceLocation
    end: SourceLocation

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


class PathStep(BaseModel):
    location: Span
    description: str
    step_number: int


class Diagnostic(BaseModel):
    rule_id: str
    message: str
    file_path: str
    location: Span
    resource_type: str
    resource_variable: Optional[str] = None
    acquisition_location: Optional[Span] = None
    release_location: Optional[Span] = None
    execution_path: List[PathStep] = Field(default_factory=list)
    severity: Severity = Severity.ERROR
    confidence: Confidence = Confidence.HIGH
    reason: str
