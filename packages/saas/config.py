import os
from pydantic import BaseModel, Field


class SaaSConfig(BaseModel):
    """Configuration settings for the LeakGuard SaaS Control Plane."""

    db_url: str = Field(
        default_factory=lambda: os.getenv(
            "LEAKGUARD_DATABASE_URL",
            os.getenv("DATABASE_URL", "postgresql://postgres:Deepak2003@localhost:5432/leakguard_db"),
        )
    )
    secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "LEAKGUARD_JWT_SECRET", "leakguard-super-secret-jwt-key-2026-saas-control-plane"
        )
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    rate_limit_requests_per_minute: int = 120
    environment: str = Field(default_factory=lambda: os.getenv("LEAKGUARD_ENV", "production"))

    # GitHub Integration (PAT or App mode)
    # SECURITY: Never hardcode. Set via environment variables only.
    github_token: str = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "")
    )
    github_webhook_secret: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET", "")
    )
    github_app_id: str = Field(
        default_factory=lambda: os.getenv("GITHUB_APP_ID", "")
    )
    github_app_private_key: str = Field(
        default_factory=lambda: os.getenv("GITHUB_APP_PRIVATE_KEY", "")
    )
    github_installation_id: str = Field(
        default_factory=lambda: os.getenv("GITHUB_INSTALLATION_ID", "")
    )
    # LeakGuard portal URL (used in PR review comment links)
    leakguard_portal_url: str = Field(
        default_factory=lambda: os.getenv("LEAKGUARD_PORTAL_URL", "http://localhost:3000")
    )


settings = SaaSConfig()
