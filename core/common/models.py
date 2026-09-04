from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Classification(str, Enum):
    SAFE = "SAFE"
    DEFINITE_LEAK = "DEFINITE_LEAK"
    POTENTIAL_LEAK = "POTENTIAL_LEAK"
    UNKNOWN = "UNKNOWN"


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
    UNKNOWN = "UNKNOWN"


class SourceLocation(BaseModel):
    line: int = Field(..., description="1-indexed line number")
    column: int = Field(..., description="1-indexed column number")
    byte_offset: Optional[int] = Field(None, description="0-indexed byte offset")

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


class Span(BaseModel):
    start: SourceLocation
    end: SourceLocation

    def __str__(self) -> str:
        return f"{self.start.line}:{self.start.column}-{self.end.line}:{self.end.column}"


class ResourceSymbol(BaseModel):
    id: str
    variable_name: str
    resource_type: str
    acquisition_span: Span
    owning_scope: str = "method"
    is_try_with_resources: bool = False


class PathStep(BaseModel):
    step_number: int
    location: Span
    description: str
    state_at_step: ResourceState = ResourceState.OPEN_MUST_CLOSE


class Diagnostic(BaseModel):
    finding_id: str = Field(..., description="Deterministic unique identifier")
    rule_id: str = Field(default="RULE_LEAK_001")
    classification: Classification = Classification.DEFINITE_LEAK
    message: str
    file_path: str
    location: Span
    resource_type: str
    resource_variable: Optional[str] = None
    acquisition_location: Optional[Span] = None
    release_location: Optional[Span] = None
    execution_path: List[PathStep] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    severity: Severity = Severity.ERROR
    reason: str
