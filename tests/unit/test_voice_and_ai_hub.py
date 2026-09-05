import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from services.voice.announcer import VoiceAnnouncer
from packages.saas.app import create_app, seed_standard_rules
from packages.saas.db.database import Base, get_db
from packages.saas.db.models import Organization, User, UserOrgRole, RoleEnum
from packages.saas.auth.security import create_access_token
from interfaces.cli.main import app as cli_app

runner = CliRunner()


# 1. VoiceAnnouncer Unit Tests
def test_voice_announcer_instantiation():
    announcer = VoiceAnnouncer(enabled=True)
    # Should run without error
    announcer.speak_scan_result(passed=True, leak_count=0, async_mode=True)
    announcer.speak_scan_result(passed=False, leak_count=3, first_rule="LG-DB-001", async_mode=True)


# 2. FastAPI AI Agents Hub & Individual Execution Tests
def test_ai_agents_hub_fastapi_endpoints():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    seed_standard_rules(db)
    org = Organization(name="AI Hub Org", slug="ai-hub-org")
    user = User(email="dev@aihub.com", hashed_password="pw")
    db.add(org)
    db.add(user)
    db.commit()

    user_org = UserOrgRole(user_id=user.id, org_id=org.id, role=RoleEnum.DEVELOPER.value)
    db.add(user_org)
    db.commit()

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    token = create_access_token({"sub": user.id})
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org.id}

    # GET Agents Catalog
    resp = client.get("/ai/agents", headers=headers)
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) == 10
    agent_names = [a["name"] for a in catalog]
    assert "Resource Hunter Agent" in agent_names
    assert "Verification Sandbox Agent" in agent_names

    # POST Run Individual Agent
    resp = client.post(
        "/ai/agents/hunter/run",
        headers=headers,
        json={"file_path": "app.py", "source_code": "f = open('a.txt')", "line_number": 1, "resource_type": "FILE", "resource_variable": "f"},
    )
    assert resp.status_code == 200
    assert "status" in resp.json() or "summary" in resp.json()

    db.close()


# 3. CLI Speak Command Test
def test_cli_speak_command():
    res = runner.invoke(cli_app, ["speak", "Testing LeakGuard Voice Alerts"])
    assert res.exit_code == 0
