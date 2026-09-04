import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.ai.remediator import AIRemediator
from services.ai.validator import PatchValidator
from packages.saas.app import create_app, seed_standard_rules
from packages.saas.db.database import Base, get_db, init_db
from packages.saas.db.models import Finding
from core.common.models import Diagnostic, Span, SourceLocation, Severity, Confidence, Classification


@pytest.fixture
def sample_diagnostic():
    loc = Span(start=SourceLocation(line=2, column=4), end=SourceLocation(line=2, column=25))
    return Diagnostic(
        finding_id="FND-100",
        rule_id="LG-FILE-001",
        message="Unclosed File Stream",
        file_path="app.py",
        location=loc,
        resource_type="FILE",
        resource_variable="f",
        severity=Severity.ERROR,
        confidence=Confidence.HIGH,
        classification=Classification.DEFINITE_LEAK,
        reason="File handle opened without close",
        remediation="Use with open(...) as f context manager",
    )


def test_ai_remediator_explanation(sample_diagnostic):
    remediator = AIRemediator()
    explanation = remediator.explain_finding(sample_diagnostic)
    assert "LG-FILE-001" in explanation
    assert "line 2" in explanation
    assert "unclosed FILE resource 'f'" in explanation


def test_ai_remediator_local_synthesizer(sample_diagnostic):
    remediator = AIRemediator()
    original_code = "def read_data():\n    f = open('test.txt')\n    return f.read()\n"
    res = remediator.generate_candidate_patch(original_code, sample_diagnostic)

    assert "with open('test.txt') as f:" in res.candidate_code
    assert res.provider == "Local AST Pattern Synthesizer"
    assert not res.is_ai_generated


def test_patch_validator_9_step_pipeline(sample_diagnostic):
    validator = PatchValidator()
    original_code = "def read_data():\n    f = open('test.txt')\n    return f.read()\n"
    candidate_code = "def read_data():\n    with open('test.txt') as f:\n        return f.read()\n"

    report = validator.validate_patch(original_code, candidate_code, sample_diagnostic, file_name="app.py")

    assert report.syntax_valid is True
    assert report.original_finding_cleared is True
    assert report.new_findings_count == 0
    assert report.is_valid is True
    assert report.requires_human_approval is True
    assert "--- a/app.py" in report.unified_diff
    assert "+++ b/app.py" in report.unified_diff
    assert len(report.validation_steps) >= 5


def test_patch_validator_syntax_error_rejection(sample_diagnostic):
    validator = PatchValidator()
    original_code = "def read_data():\n    f = open('test.txt')\n    return f.read()\n"
    invalid_candidate = "def read_data():\n    with open('test.txt') as f:\n        return f.read("  # Syntax error

    report = validator.validate_patch(original_code, invalid_candidate, sample_diagnostic, file_name="app.py")

    assert report.syntax_valid is False
    assert report.is_valid is False
    assert "Syntax error" in (report.failure_reason or "")


def test_api_remediate_and_apply_patch_endpoints():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed
    db = TestingSessionLocal()
    seed_standard_rules(db)
    db.close()

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        # Signup
        signup = client.post("/api/v1/auth/signup", json={
            "email": "ai_dev@acme.com",
            "password": "Password123!",
            "full_name": "AI Dev",
            "organization_name": "Acme AI",
        })
        token = signup.json()["access_token"]
        org_id = signup.json()["organization_id"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

        # Ingest scan with leak finding
        scan_payload = {
            "repository_name": "ai-test-repo",
            "commit_sha": "HEAD",
            "branch": "main",
            "scanned_files_count": 1,
            "duration_seconds": 0.1,
            "policy_passed": False,
            "findings": [
                {
                    "rule_id": "LG-FILE-001",
                    "file_path": "services/logger.py",
                    "line_number": 2,
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "classification": "DEFINITE_LEAK",
                    "title": "Unclosed File Stream",
                    "description": "File handle opened without close",
                    "fingerprint": "LG-FILE-001:services/logger.py:2",
                }
            ],
        }
        res_scan = client.post("/api/v1/scans", json=scan_payload, headers=headers)
        assert res_scan.status_code == 201
        finding_id = res_scan.json()["findings"][0]["id"]

        # Call Remediate Endpoint
        res_rem = client.post(f"/api/v1/findings/{finding_id}/remediate", headers=headers)
        assert res_rem.status_code == 200
        rem_data = res_rem.json()
        assert rem_data["finding_id"] == finding_id
        assert "validation_report" in rem_data
        assert rem_data["validation_report"]["is_valid"] is True

        # Apply Patch without approval -> 400 Bad Request
        res_reject = client.post(f"/api/v1/findings/{finding_id}/apply-patch", json={"approved": False}, headers=headers)
        assert res_reject.status_code == 400

        # Apply Patch with approval -> 200 OK & Status RESOLVED
        res_apply = client.post(f"/api/v1/findings/{finding_id}/apply-patch", json={"approved": True}, headers=headers)
        assert res_apply.status_code == 200
        assert res_apply.json()["status"] == "RESOLVED"
