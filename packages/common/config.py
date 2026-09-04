from typing import List, Optional
from pydantic import BaseModel, Field
from packages.common.models import Severity


class LeakGuardConfig(BaseModel):
    fail_on_severity: Severity = Field(default=Severity.ERROR, description="Minimum severity to return non-zero exit code")
    include_patterns: List[str] = Field(default_factory=lambda: ["**/*.java"])
    exclude_patterns: List[str] = Field(default_factory=lambda: ["**/test/**", "**/Test*.java", "**/build/**", "**/target/**"])
    track_custom_autocloseable: bool = Field(default=True)
    custom_resource_classes: List[str] = Field(default_factory=list)
    custom_release_methods: List[str] = Field(default_factory=lambda: ["close", "closeQuietly", "dispose", "release"])
    output_format: str = Field(default="cli", description="Format: cli | json | sarif")
    report_file: Optional[str] = Field(default=None)
