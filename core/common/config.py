from typing import List, Optional
from pydantic import BaseModel, Field
from core.common.models import Severity, Confidence


class LeakGuardConfig(BaseModel):
    fail_on_severity: Severity = Field(default=Severity.ERROR)
    fail_on: str = Field(default="error", description="error | warning | critical | info | none")
    min_confidence: Confidence = Field(default=Confidence.LOW)
    min_severity: Severity = Field(default=Severity.INFO)
    include_patterns: List[str] = Field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: List[str] = Field(default_factory=lambda: ["**/venv/**", "**/.venv/**", "**/__pycache__/**", "**/build/**", "**/dist/**", "**/.git/**", "**/.pytest_cache/**"])
    track_custom_autocloseable: bool = Field(default=True)
    custom_resource_classes: List[str] = Field(default_factory=list)
    custom_release_methods: List[str] = Field(default_factory=lambda: ["close", "closeQuietly", "dispose", "release"])
    output_format: str = Field(default="text", description="text | json | sarif")
    report_file: Optional[str] = Field(default=None)
    max_file_size_bytes: int = Field(default=5_000_000, description="5 MB file size limit for analysis")
    per_file_timeout_seconds: int = Field(default=30)
    workers: int = Field(default=1, description="Number of parallel worker processes")
    changed_only: bool = Field(default=False, description="Scan only git changed files")
    baseline_file: Optional[str] = Field(default=None, description="Path to baseline JSON file")
    quiet: bool = Field(default=False)
    verbose: bool = Field(default=False)

