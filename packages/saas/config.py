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


settings = SaaSConfig()
