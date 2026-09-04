from typing import List, Optional
from pydantic import BaseModel, Field
from core.common.models import Severity


class LeakGuardConfig(BaseModel):
    fail_on_severity: Severity = Field(default=Severity.ERROR)
    include_patterns: List[str] = Field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: List[str] = Field(default_factory=lambda: ["**/test_*.py", "**/tests/**", "**/venv/**", "**/__pycache__/**", "**/build/**"])
    track_custom_autocloseable: bool = Field(default=True)
    custom_resource_classes: List[str] = Field(default_factory=list)
    custom_release_methods: List[str] = Field(default_factory=lambda: ["close", "closeQuietly", "dispose", "release"])
    output_format: str = Field(default="cli", description="cli | json | sarif")
    report_file: Optional[str] = Field(default=None)
    max_file_size_bytes: int = Field(default=5_000_000, description="5 MB file size limit for analysis")
    per_file_timeout_seconds: int = Field(default=30)
