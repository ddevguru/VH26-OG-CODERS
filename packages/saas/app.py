from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from packages.saas.config import settings
from packages.saas.db.database import init_db, get_db, _SessionLocal
from packages.saas.db.models import Rule, User, Organization, UserOrgRole, Policy, RoleEnum
from packages.saas.auth.security import hash_password
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
    admin,
    ai_review,
    phase16,
    firewall_diff,
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


def seed_default_admin(db=None):
    close_after = False
    if db is None:
        db = _SessionLocal()
        close_after = True

    try:
        admin_user = db.query(User).filter(User.email == "admin@leakguard.io").first()
        if not admin_user:
            hashed_pwd = hash_password("Admin123!")
            admin_user = User(email="admin@leakguard.io", hashed_password=hashed_pwd, full_name="System Administrator")
            db.add(admin_user)
            db.flush()

            admin_org = db.query(Organization).filter(Organization.slug == "leakguard-admin").first()
            if not admin_org:
                admin_org = Organization(name="LeakGuard Admin Org", slug="leakguard-admin")
                db.add(admin_org)
                db.flush()

            role = UserOrgRole(user_id=admin_user.id, org_id=admin_org.id, role=RoleEnum.ADMIN.value)
            db.add(role)

            policy = Policy(org_id=admin_org.id, name="Default Security Policy", min_severity="MEDIUM", is_default=True)
            db.add(policy)

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
    seed_default_admin()
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
    app.include_router(admin.router, prefix=api_prefix)
    app.include_router(ai_review.router)
    app.include_router(phase16.router)
    app.include_router(firewall_diff.router)

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
