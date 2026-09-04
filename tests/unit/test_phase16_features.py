import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from core.common.models import Diagnostic, Span, SourceLocation, Severity, Confidence, Classification
from core.analysis.scorer import RiskScorer, RiskScore, RiskLevel
from core.ownership.graph import ResourceOwnershipGraph, OwnershipNode, OwnershipEdge, EdgeRelationship
from core.analysis.what_if import WhatIfEngine, WhatIfResult
from services.ai.strategies import (
    ContextManagerStrategy,
    TryFinallyStrategy,
    CloseInsertionStrategy,
)
from services.ai.auto_fixer import AutoFixerEngine, PatchResult
from packages.saas.app import create_app, seed_standard_rules
from packages.saas.db.database import Base, get_db
from packages.saas.db.models import Finding, Organization, User, UserOrgRole, RoleEnum
from packages.saas.auth.security import create_access_token
from interfaces.cli.main import app as cli_app

runner = CliRunner()


@pytest.fixture
def sample_diag():
    loc = Span(start=SourceLocation(line=2, column=4), end=SourceLocation(line=2, column=25))
    return Diagnostic(
        finding_id="FND-P16-001",
        rule_id="RULE_DB_001",
        message="Unclosed Database Connection",
        file_path="src/database.py",
        location=loc,
        resource_type="DATABASE",
        resource_variable="conn",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK,
        reason="Database connection acquired without cleanup on exception branch",
    )


# 1. Deterministic Risk Scorer Tests
def test_risk_scorer_bounded_range(sample_diag):
    scorer = RiskScorer()
    score_result = scorer.calculate_score(sample_diag)

    assert isinstance(score_result, RiskScore)
    assert 0 <= score_result.score <= 100
    assert score_result.level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert len(score_result.factors) > 0


def test_risk_scorer_category_weights():
    loc = Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=10))

    db_diag = Diagnostic(
        finding_id="F1", rule_id="R1", message="DB", file_path="db.py", location=loc,
        resource_type="DATABASE", resource_variable="db", severity=Severity.CRITICAL,
        confidence=Confidence.HIGH, classification=Classification.DEFINITE_LEAK, reason="Leak"
    )
    file_diag = Diagnostic(
        finding_id="F2", rule_id="R2", message="File", file_path="f.py", location=loc,
        resource_type="FILE", resource_variable="f", severity=Severity.WARNING,
        confidence=Confidence.LOW, classification=Classification.POTENTIAL_LEAK, reason="Leak"
    )

    scorer = RiskScorer()
    db_score = scorer.calculate_score(db_diag)
    file_score = scorer.calculate_score(file_diag)

    assert db_score.score > file_score.score


# 2. Resource Ownership Graph Tests
def test_resource_ownership_graph_building(sample_diag):
    graph = ResourceOwnershipGraph.from_diagnostic(sample_diag)
    dumped = graph.model_dump()

    assert "nodes" in dumped
    assert "edges" in dumped
    assert len(graph.nodes) >= 2
    resource_node = [n for n in graph.nodes if n.variable == "conn"][0]
    assert resource_node.resource_type == "DATABASE"


def test_resource_ownership_graph_child_nodes(sample_diag):
    graph = ResourceOwnershipGraph.from_diagnostic(sample_diag)
    child_node = OwnershipNode(
        resource_id="node_cursor",
        resource_type="CURSOR",
        variable="cur",
        owner="test_fn",
        leak_status="DEFINITE_LEAK",
    )
    edge = OwnershipEdge(
        source_id="node_conn",
        target_id="node_cursor",
        relationship=EdgeRelationship.DEPENDS_ON,
        label="Cursor derived from connection",
    )
    graph.nodes.append(child_node)
    graph.edges.append(edge)

    assert len(graph.nodes) == 3
    assert len(graph.edges) == 3
    assert graph.edges[-1].relationship == EdgeRelationship.DEPENDS_ON


# 3. What-If Analysis Engine Tests
def test_what_if_engine_simulation():
    engine = WhatIfEngine()
    code = (
        "def query_db():\n"
        "    conn = connect()\n"
        "    cursor = conn.cursor()\n"
        "    res = cursor.execute('SELECT 1')\n"
        "    return res\n"
    )
    result = engine.analyze_exception_point(source_code=code, line_number=4, file_path="app.py")

    assert isinstance(result, WhatIfResult)
    assert result.source_location == "app.py:4"
    assert result.function_name == "query_db"
    assert len(result.hypothetical_path) > 0


# 4. Auto Fixer Strategy & Verification Tests
def test_fix_strategies(sample_diag):
    code = "def process():\n    f = open('data.txt')\n    return f.read()\n"
    sample_diag.resource_variable = "f"

    cm_strat = ContextManagerStrategy()
    tf_strat = TryFinallyStrategy()
    close_strat = CloseInsertionStrategy()

    cm_code, _ = cm_strat.apply(code, sample_diag)
    tf_code, _ = tf_strat.apply(code, sample_diag)
    close_code, _ = close_strat.apply(code, sample_diag)

    assert "with open('data.txt') as f:" in cm_code
    assert "try:" in tf_code
    assert "f.close()" in close_code


def test_auto_fixer_engine_generate_and_verify(sample_diag):
    engine = AutoFixerEngine()
    code = "def read_file():\n    f = open('test.txt')\n    return f.read()\n"
    sample_diag.resource_variable = "f"

    res = engine.generate_and_verify(source_code=code, diagnostic=sample_diag, strategy_name="context-manager")

    assert isinstance(res, PatchResult)
    assert res.is_verified is True
    assert res.verification_status == "VERIFIED_FIX"
    assert len(res.verification_steps) > 0


# 5. FastAPI Endpoints Integration Tests
def test_phase16_fastapi_endpoints():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    seed_standard_rules(db)
    org = Organization(name="Phase16 Test Org", slug="phase16-test-org")
    user = User(email="dev@phase16.com", hashed_password="pw")
    db.add(org)
    db.add(user)
    db.commit()

    user_org = UserOrgRole(user_id=user.id, org_id=org.id, role=RoleEnum.DEVELOPER.value)
    finding = Finding(
        org_id=org.id,
        scan_id="scan_1",
        rule_id="RULE_DB_001",
        file_path="db.py",
        line_number=10,
        severity="CRITICAL",
        confidence="HIGH",
        classification="DEFINITE_LEAK",
        title="Unclosed 'conn' Connection",
        fingerprint="fp16",
        status="OPEN",
    )
    db.add(user_org)
    db.add(finding)
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

    # GET Ownership Graph
    resp = client.get(f"/api/v1/findings/{finding.id}/ownership-graph", headers=headers)
    assert resp.status_code == 200
    assert "nodes" in resp.json()

    # GET Risk Score
    resp = client.get(f"/api/v1/findings/{finding.id}/risk-score", headers=headers)
    assert resp.status_code == 200
    assert "score" in resp.json()

    # POST What-If Analysis
    resp = client.post(
        "/api/v1/analysis/what-if",
        headers=headers,
        json={"source_code": "def fn():\n    f = open('a.txt')\n    x = 1/0", "line_number": 3, "file_path": "a.py"},
    )
    assert resp.status_code == 200
    assert "source_location" in resp.json()

    # POST Fix
    resp = client.post(
        f"/api/v1/findings/{finding.id}/fix",
        headers=headers,
        json={"source_code": "def read_file():\n    f = open('a.txt')\n    return f.read()\n", "strategy": "context-manager"},
    )
    assert resp.status_code == 200
    assert "candidate_code" in resp.json()

    # POST Verify Patch
    resp = client.post(
        "/api/v1/patches/verify",
        headers=headers,
        json={
            "patch_id": "p1",
            "original_code": "def read_file():\n    f = open('a.txt')\n    return f.read()\n",
            "candidate_code": "def read_file():\n    with open('a.txt') as f:\n        return f.read()\n",
            "finding_id": finding.id,
            "file_name": "a.py",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["verification_status"] == "VERIFIED_FIX"

    db.close()


# 6. Typer CLI Phase 16 Commands Test
def test_phase16_cli_commands(tmp_path):
    test_file = tmp_path / "sample.py"
    test_file.write_text("def run():\n    f = open('demo.txt')\n    return f.read()\n")

    # Risk command
    res = runner.invoke(cli_app, ["risk", str(test_file)])
    assert res.exit_code == 0
    assert "RISK SCORE" in res.output or "Risk" in res.output

    # Ownership command
    res = runner.invoke(cli_app, ["ownership", str(test_file)])
    assert res.exit_code == 0
    assert "RESOURCE OWNERSHIP GRAPH" in res.output or "Ownership" in res.output

    # What-If command
    res = runner.invoke(cli_app, ["what-if", "--file", str(test_file), "--line", "2"])
    assert res.exit_code == 0
    assert "WHAT-IF" in res.output or "Simulation" in res.output
