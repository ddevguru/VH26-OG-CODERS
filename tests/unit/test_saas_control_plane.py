import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.saas.app import create_app, seed_standard_rules
from packages.saas.db.database import Base, get_db, init_db
from packages.saas.db.models import (
    User, Organization, UserOrgRole, RoleEnum, Repository, Scan, Finding, Policy, Baseline, Suppression, Integration, AuditEvent, Rule
)
from services.saas.sync import upload_scan_results
from core.common.models import ScanResult, Diagnostic, Span, SourceLocation, Severity, Confidence, Classification


@pytest.fixture
def test_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    db = Session()
    seed_standard_rules(db)
    db.close()

    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_engine):
    app = create_app()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_auth_signup_and_login(client):
    # Test Signup
    signup_payload = {
        "email": "owner@acme.com",
        "password": "Password123!",
        "full_name": "Alice Acme",
        "organization_name": "Acme Corp",
    }
    resp = client.post("/api/v1/auth/signup", json=signup_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "Owner"
    token = data["access_token"]

    # Test Login
    login_payload = {"email": "owner@acme.com", "password": "Password123!"}
    resp_login = client.post("/api/v1/auth/login", json=login_payload)
    assert resp_login.status_code == 200, resp_login.text
    assert "access_token" in resp_login.json()

    # Test /me
    resp_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_me.status_code == 200, resp_me.text
    me_data = resp_me.json()
    assert me_data["email"] == "owner@acme.com"
    assert len(me_data["organizations"]) == 1
    assert me_data["organizations"][0]["role"] == "Owner"


def test_tenant_isolation_and_rbac(client):
    # Signup Tenant 1 (Acme)
    resp1 = client.post("/api/v1/auth/signup", json={
        "email": "alice@acme.com",
        "password": "Password123!",
        "full_name": "Alice Acme",
        "organization_name": "Acme Corp",
    })
    token1 = resp1.json()["access_token"]
    org1_id = resp1.json()["organization_id"]

    # Signup Tenant 2 (Beta)
    resp2 = client.post("/api/v1/auth/signup", json={
        "email": "bob@beta.com",
        "password": "Password123!",
        "full_name": "Bob Beta",
        "organization_name": "Beta Inc",
    })
    token2 = resp2.json()["access_token"]
    org2_id = resp2.json()["organization_id"]

    # Tenant 1 creates repository
    resp_repo = client.post(
        "/api/v1/repositories",
        json={"name": "acme-secret-repo"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-ID": org1_id},
    )
    assert resp_repo.status_code == 201, resp_repo.text

    # Tenant 2 tries to view Tenant 1's org data with Org 1 ID in header -> Should receive 403 Forbidden
    resp_cross = client.get(
        "/api/v1/repositories",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-ID": org1_id},
    )
    assert resp_cross.status_code == 403

    # Tenant 2 lists own repos -> Should NOT see Tenant 1 repo
    resp_t2_repos = client.get(
        "/api/v1/repositories",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-ID": org2_id},
    )
    assert resp_t2_repos.status_code == 200
    assert len(resp_t2_repos.json()["items"]) == 0


def test_scan_ingestion_metadata_only(client):
    # Signup
    signup = client.post("/api/v1/auth/signup", json={
        "email": "dev@acme.com",
        "password": "Password123!",
        "full_name": "Dev User",
        "organization_name": "Acme Dev",
    })
    token = signup.json()["access_token"]
    org_id = signup.json()["organization_id"]

    scan_payload = {
        "repository_name": "backend-service",
        "commit_sha": "abc1234def",
        "branch": "feature/leak-fix",
        "scanned_files_count": 42,
        "duration_seconds": 0.45,
        "policy_passed": False,
        "findings": [
            {
                "rule_id": "LG-FILE-001",
                "file_path": "services/db.py",
                "line_number": 28,
                "severity": "HIGH",
                "confidence": "HIGH",
                "classification": "DEFINITE_LEAK",
                "title": "Unclosed File Handle",
                "description": "File opened at line 28 is not closed",
                "fingerprint": "LG-FILE-001:services/db.py:28",
            }
        ],
    }

    resp = client.post(
        "/api/v1/scans",
        json=scan_payload,
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 201, resp.text
    scan_data = resp.json()
    assert scan_data["total_findings"] == 1
    assert scan_data["findings"][0]["fingerprint"] == "LG-FILE-001:services/db.py:28"
    assert "source_code" not in scan_data["findings"][0]

    # Query Findings
    resp_f = client.get(
        "/api/v1/findings",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp_f.status_code == 200, resp_f.text
    assert len(resp_f.json()["items"]) == 1
    finding_id = resp_f.json()["items"][0]["id"]

    # Update Finding status
    resp_patch = client.patch(
        f"/api/v1/findings/{finding_id}/status",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp_patch.status_code == 200, resp_patch.text
    assert resp_patch.json()["status"] == "RESOLVED"


def test_policies_baselines_integrations_audit(client):
    signup = client.post("/api/v1/auth/signup", json={
        "email": "sec@acme.com",
        "password": "Password123!",
        "full_name": "Sec Admin",
        "organization_name": "Acme Enterprise",
    })
    token = signup.json()["access_token"]
    org_id = signup.json()["organization_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # Policies
    resp_pol = client.post(
        "/api/v1/policies",
        json={"name": "Strict Policy", "min_severity": "HIGH", "fail_on_leak": True},
        headers=headers,
    )
    assert resp_pol.status_code == 201, resp_pol.text
    assert resp_pol.json()["name"] == "Strict Policy"

    # Integrations with secret masking
    resp_int = client.post(
        "/api/v1/integrations",
        json={
            "name": "Production GitHub Webhook",
            "integration_type": "github",
            "config": {"webhook_url": "https://github.com/webhook", "api_secret_token": "super_secret_github_token_12345"},
        },
        headers=headers,
    )
    assert resp_int.status_code == 201, resp_int.text
    masked_cfg = resp_int.json()["config"]
    assert masked_cfg["api_secret_token"] != "super_secret_github_token_12345"
    assert "..." in masked_cfg["api_secret_token"] or "********" in masked_cfg["api_secret_token"]

    # Audit Log Query
    resp_audit = client.get("/api/v1/audit-log", headers=headers)
    assert resp_audit.status_code == 200, resp_audit.text
    events = resp_audit.json()["items"]
    assert len(events) >= 2
    actions = [e["action"] for e in events]
    assert "create_integration" in actions
    assert "create_policy" in actions


def test_local_sync_client(client):
    # Setup Auth
    signup = client.post("/api/v1/auth/signup", json={
        "email": "ci@acme.com",
        "password": "Password123!",
        "full_name": "CI Runner",
        "organization_name": "Acme CI",
    })
    token = signup.json()["access_token"]
    org_id = signup.json()["organization_id"]

    # Prepare local scan result mock
    loc = Span(start=SourceLocation(line=12, column=4), end=SourceLocation(line=12, column=20))
    diag = Diagnostic(
        finding_id="FND-001",
        rule_id="LG-FILE-001",
        message="Unclosed file resource",
        file_path="app.py",
        location=loc,
        resource_type="FILE",
        severity=Severity.ERROR,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK,
        reason="Unclosed file resource",
        remediation="Use with open(...) context manager",
    )
    scan_result = ScanResult(
        status="success",
        scanned_files_count=5,
        duration_seconds=0.12,
        diagnostics=[diag],
        policy_passed=False,
    )

    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}
    payload = {
        "repository_name": "cli-sync-repo",
        "commit_sha": "HEAD",
        "branch": "main",
        "scanned_files_count": scan_result.scanned_files_count,
        "duration_seconds": scan_result.duration_seconds,
        "policy_passed": scan_result.policy_passed,
        "findings": [
            {
                "rule_id": d.rule_id,
                "file_path": str(d.file_path),
                "line_number": d.location.start.line,
                "severity": str(d.severity),
                "confidence": str(d.confidence),
                "classification": str(d.classification),
                "title": d.message,
                "description": d.remediation or "",
                "fingerprint": f"{d.rule_id}:{d.file_path}:{d.location.start.line}",
            }
            for d in scan_result.diagnostics
        ],
    }
    res = client.post("/api/v1/scans", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    result = res.json()
    assert result["total_findings"] == 1
    assert result["findings"][0]["rule_id"] == "LG-FILE-001"
