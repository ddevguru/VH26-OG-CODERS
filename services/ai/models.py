import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification


class ReviewMode(str, Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    SECURITY = "security"
    SENIOR_ENGINEER = "senior-engineer"
    DEVELOPER_FRIENDLY = "developer-friendly"


class AgentStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.COMPLETED
    finding_id: Optional[str] = None
    summary: str = ""
    details: str = ""
    recommendations: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FixCandidate(BaseModel):
    finding_id: str
    original_code: str
    candidate_patch: str
    unified_diff: str = ""
    explanation: str = ""
    strategy: str = "context_manager"
    provider: str = "Ollama"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class VerificationResult(BaseModel):
    finding_id: str
    status: str  # "VERIFIED_FIX", "REJECTED", "SYNTAX_ERROR"
    is_verified: bool = False
    before_classification: Classification = Classification.DEFINITE_LEAK
    after_classification: Optional[Classification] = Classification.SAFE
    original_finding_cleared: bool = False
    new_findings_introduced: int = 0
    unified_diff: str = ""
    reason: str = ""
    verification_steps: List[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentActivityLog(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%H:%M:%S"))
    agent_name: str
    status: AgentStatus
    duration_ms: float
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    trace_id: Optional[str] = None
    details: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReviewResult(BaseModel):
    target: str = "project"  # "project", "pr", "commit", "file", "finding"
    review_mode: ReviewMode = ReviewMode.DETAILED
    total_files_reviewed: int = 0
    new_leaks_count: int = 0
    resolved_leaks_count: int = 0
    overall_status: str = "PASSED"  # "PASSED", "FAILED"
    summary: str = ""
    findings_explanations: List[Dict[str, Any]] = Field(default_factory=list)
    agent_results: List[AgentResult] = Field(default_factory=list)
    activity_timeline: List[AgentActivityLog] = Field(default_factory=list)
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    trace_id: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
