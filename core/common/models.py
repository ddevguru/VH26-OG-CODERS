from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    FILE = "FILE"
    DATABASE = "DATABASE"
    SOCKET = "SOCKET"
    HTTP = "HTTP"
    SUBPROCESS = "SUBPROCESS"
    LOCK = "LOCK"
    TEMPFILE = "TEMPFILE"
    CUSTOM = "CUSTOM"


class ResourceState(str, Enum):
    UNACQUIRED = "UNACQUIRED"
    UNSEEN = "UNACQUIRED"
    OPEN = "OPEN_MUST_CLOSE"
    OPEN_MUST_CLOSE = "OPEN_MUST_CLOSE"
    CLOSED = "CLOSED"
    TRANSFERRED = "TRANSFERRED"
    MAYBE_LEAKED = "MAYBE_LEAKED"
    LEAKED = "LEAKED"
    ESCAPED = "ESCAPED"
    UNKNOWN = "UNKNOWN"


class OwnershipState(str, Enum):
    OWNED = "OWNED"
    BORROWED = "BORROWED"
    TRANSFERRED = "TRANSFERRED"
    ESCAPED = "ESCAPED"
    UNKNOWN = "UNKNOWN"


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


class ResourceIdentity(BaseModel):
    id: str
    variable_name: str
    resource_type: Union[ResourceType, str] = Field(default=ResourceType.FILE)
    scope_id: str = "global"
    acquisition_span: Span
    is_try_with_resources: bool = False


ResourceSymbol = ResourceIdentity


class ResourceAcquisition(BaseModel):
    resource_id: str
    location: Span
    expression_str: str
    resource_type: ResourceType


class ResourceRelease(BaseModel):
    resource_id: str
    location: Span
    method_name: str


class ControlFlowNode(BaseModel):
    block_id: int
    statements_count: int
    is_entry: bool = False
    is_exit: bool = False
    is_exceptional_exit: bool = False


class ControlFlowEdge(BaseModel):
    source_id: int
    target_id: int
    edge_type: str = "NORMAL"
    label: Optional[str] = None


class PathStep(BaseModel):
    step_number: int
    location: Span
    description: str
    state_at_step: ResourceState = ResourceState.OPEN


import hashlib


class Diagnostic(BaseModel):
    finding_id: str = Field(..., description="Deterministic unique identifier")
    rule_id: str = Field(default="RULE_LEAK_001")
    classification: Classification = Classification.DEFINITE_LEAK
    message: str
    file_path: str
    location: Span
    resource_type: str
    resource_variable: Optional[str] = None
    function_name: Optional[str] = None
    acquisition_location: Optional[Span] = None
    release_location: Optional[Span] = None
    execution_path: List[PathStep] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    severity: Severity = Severity.ERROR
    reason: str
    remediation: str = "Use a context manager ('with' or 'async with') to ensure resource cleanup."

    @property
    def fingerprint(self) -> str:
        norm_path = self.file_path.replace("\\", "/").lower()
        raw = f"{self.rule_id}:{norm_path}:{self.resource_type}:{self.resource_variable or ''}:{self.location.start.line}:{self.classification.value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class Finding(BaseModel):
    id: str
    diagnostic: Diagnostic
    fingerprint: str


class Policy(BaseModel):
    fail_on_severity: Severity = Severity.ERROR
    fail_on_confidence: Confidence = Confidence.MEDIUM
    fail_on: str = "error"
    confidence_threshold: float = 0.85
    max_allowed_leaks: int = 0


class PolicyEvaluationResult(BaseModel):
    passed: bool = True
    blocking_findings: List[Diagnostic] = Field(default_factory=list)
    suppressed_findings: List[Diagnostic] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)



class ScanStatistics(BaseModel):
    files_scanned: int = 0
    files_skipped: int = 0
    functions_analyzed: int = 0
    resources_analyzed: int = 0
    findings_count: int = 0
    duration_seconds: float = 0.0
    throughput_files_per_sec: float = 0.0


class ScanResult(BaseModel):
    status: str = "success"
    scanned_files_count: int = 0
    skipped_files_count: int = 0
    duration_seconds: float = 0.0
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    statistics: ScanStatistics = Field(default_factory=ScanStatistics)
    baseline_suppressed_count: int = 0
    blocking_findings_count: int = 0
    policy_passed: bool = True


class RuleDefinition(BaseModel):
    rule_id: str
    category: ResourceType
    acquisition_targets: List[str]
    release_methods: List[str]
    severity: Severity = Severity.ERROR
    description: str

