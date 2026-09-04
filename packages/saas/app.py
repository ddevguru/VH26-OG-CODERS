from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from packages.saas.config import settings
from packages.saas.db.database import init_db, get_db, _SessionLocal
from packages.saas.db.models import Rule
from packages.saas.middleware.rate_limiter import RateLimiterMiddleware
from packages.saas.routers import (
    auth,
    organizations,
    repositories,
    scans,
    findings,
    rules,
    policies,
    baselines,
    integrations,
    audit_log,
)


def seed_standard_rules(db=None):
    close_after = False
    if db is None:
        db = _SessionLocal()
        close_after = True

    try:
        if db.query(Rule).count() == 0:
            standard_rules = [
                Rule(rule_id="LG-FILE-001", name="Unclosed File Stream", category="File System", default_severity="HIGH", default_confidence="HIGH", description="File handle opened without close or context manager", is_custom=False),
                Rule(rule_id="LG-DB-001", name="Unclosed DB Connection", category="Database", default_severity="CRITICAL", default_confidence="HIGH", description="Database connection or cursor not released", is_custom=False),
                Rule(rule_id="LG-NET-001", name="Unclosed Socket", category="Networking", default_severity="HIGH", default_confidence="HIGH", description="Network socket handle leaked", is_custom=False),
                Rule(rule_id="LG-HTTP-001", name="Unclosed HTTP Client Session", category="HTTP Client", default_severity="MEDIUM", default_confidence="HIGH", description="HTTP client session or response stream leaked", is_custom=False),
                Rule(rule_id="LG-PROC-001", name="Unterminated Subprocess", category="Subprocess", default_severity="HIGH", default_confidence="HIGH", description="Subprocess handle initialized without wait/terminate/kill", is_custom=False),
            ]
            db.add_all(standard_rules)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        if close_after:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_standard_rules()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeakGuard SaaS Control Plane",
        description="Commercial Multi-Tenant Security & Static Resource Leak Management API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Security Headers & CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate Limiter Middleware
    app.add_middleware(RateLimiterMiddleware)

    # Register Routers under /api/v1
    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(organizations.router, prefix=api_prefix)
    app.include_router(repositories.router, prefix=api_prefix)
    app.include_router(scans.router, prefix=api_prefix)
    app.include_router(findings.router, prefix=api_prefix)
    app.include_router(rules.router, prefix=api_prefix)
    app.include_router(policies.router, prefix=api_prefix)
    app.include_router(baselines.router, prefix=api_prefix)
    app.include_router(integrations.router, prefix=api_prefix)
    app.include_router(audit_log.router, prefix=api_prefix)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy", "service": "leakguard-saas-control-plane", "version": "0.1.0"}

    @app.get("/", tags=["Health"])
    def root():
        return {
            "message": "Welcome to LeakGuard Commercial SaaS Control Plane API",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
