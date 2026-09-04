import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from core.common.models import Diagnostic, Span, SourceLocation, Severity, Confidence, Classification
from services.firewall.engine import FirewallEngine, FirewallPolicy, FirewallAction, FirewallResult
from services.diff.engine import PRDiffEngine, PRDiffResult
from packages.saas.app import create_app, seed_standard_rules
from packages.saas.db.database import Base, get_db
from packages.saas.db.models import Organization, User, UserOrgRole, RoleEnum
from packages.saas.auth.security import create_access_token
from interfaces.cli.main import app as cli_app

runner = CliRunner()


@pytest.fixture
def sample_diagnostics():
    loc = Span(start=SourceLocation(line=5, column=1), end=SourceLocation(line=5, column=10))

    diag_def_db = Diagnostic(
        finding_id="FND-DB-001",
        rule_id="LG-DB-001",
        message="Unclosed DB Connection",
        file_path="db.py",
        location=loc,
        resource_type="DATABASE",
        resource_variable="conn",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK,
        reason="DB connection unclosed",
    )

    diag_pot_file = Diagnostic(
        finding_id="FND-FILE-002",
        rule_id="LG-FILE-001",
        message="Unclosed File Handle",
        file_path="app.py",
        location=loc,
        resource_type="FILE",
        resource_variable="f",
        severity=Severity.WARNING,
        confidence=Confidence.MEDIUM,
        classification=Classification.POTENTIAL_LEAK,
        reason="File handle unclosed on branch",
    )

    return [diag_def_db, diag_pot_file]


# 1. FirewallEngine Unit Tests
def test_firewall_engine_default_policy(sample_diagnostics):
    engine = FirewallEngine()
    result = engine.evaluate(sample_diagnostics)

    assert isinstance(result, FirewallResult)
    assert result.passed is False
    assert result.status == "BLOCK"
    assert result.blocked_count == 1  # Definite DB leak blocked
    assert result.warned_count == 1   # Potential file leak warned
    assert len(result.blocked_findings) == 1
    assert result.blocked_findings[0].finding_id == "FND-DB-001"


def test_firewall_engine_custom_policy(sample_diagnostics):
    custom_policy = FirewallPolicy(
        definite_leak=FirewallAction.WARN,
        potential_leak=FirewallAction.ALLOW,
        database_leak=FirewallAction.WARN,
    )
    engine = FirewallEngine(custom_policy)
    result = engine.evaluate(sample_diagnostics)

    assert result.passed is True
    assert result.status == "PASS"
    assert result.blocked_count == 0
    assert result.warned_count >= 1


# 2. PRDiffEngine Unit Tests
def test_pr_diff_engine_comparison(sample_diagnostics):
    loc = Span(start=SourceLocation(line=10, column=1), end=SourceLocation(line=10, column=10))
    new_diag = Diagnostic(
        finding_id="FND-NET-003",
        rule_id="LG-NET-001",
        message="Unclosed Socket",
        file_path="net.py",
        location=loc,
        resource_type="SOCKET",
        resource_variable="sock",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK,
        reason="Socket unclosed",
    )

    before = sample_diagnostics  # 2 findings (1 DB definite, 1 File potential)
    after = [sample_diagnostics[1], new_diag]  # 2 findings (File potential, new Socket definite)

    diff_engine = PRDiffEngine()
    result = diff_engine.compare(before=before, after=after, pr_number="42")

    assert isinstance(result, PRDiffResult)
    assert result.pr_number == "42"
    assert result.before_count == 2
    assert result.after_count == 2
    assert result.resolved_count == 1  # FND-DB-001 resolved
    assert result.new_count == 1       # FND-NET-003 introduced
    assert result.resolved_findings[0].finding_id == "FND-DB-001"
    assert result.new_findings[0].finding_id == "FND-NET-003"


# 3. FastAPI REST Endpoints Tests
def test_firewall_and_pr_diff_fastapi_endpoints(sample_diagnostics):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    seed_standard_rules(db)
    org = Organization(name="Firewall Test Org", slug="firewall-test-org")
    user = User(email="dev@firewall.com", hashed_password="pw")
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

    # POST Firewall Evaluate
    diags_payload = [d.model_dump() for d in sample_diagnostics]
    resp = client.post("/api/v1/firewall/evaluate", headers=headers, json={"diagnostics": diags_payload})
    assert resp.status_code == 200
    assert resp.json()["status"] == "BLOCK"
    assert resp.json()["blocked_count"] == 1

    # POST PR Diff Compare
    resp = client.post(
        "/api/v1/diff/compare",
        headers=headers,
        json={"pr_number": "99", "before_diagnostics": diags_payload, "after_diagnostics": []},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_count"] == 2
    assert resp.json()["new_count"] == 0

    db.close()


# 4. CLI Commands Tests
def test_firewall_and_pr_diff_cli_commands(tmp_path):
    file_before = tmp_path / "before.py"
    file_before.write_text("def run():\n    f = open('a.txt')\n    return f.read()\n")

    file_after = tmp_path / "after.py"
    file_after.write_text("def run():\n    with open('a.txt') as f:\n        return f.read()\n")

    # PR Diff command
    res = runner.invoke(cli_app, ["pr-diff", "--before", str(file_before), "--after", str(file_after), "--pr", "42"])
    assert res.exit_code == 0
    assert "PR #42" in res.output or "PR LEAK DIFF" in res.output
    assert "Resolved:" in res.output or "fixed" in res.output

    # Firewall command on clean file
    res = runner.invoke(cli_app, ["firewall", str(file_after)])
    assert res.exit_code == 0
    assert "PASS" in res.output

    # Firewall command on leaking file (should block and exit code 1)
    res = runner.invoke(cli_app, ["firewall", str(file_before)])
    assert res.exit_code == 1
    assert "BLOCK" in res.output
