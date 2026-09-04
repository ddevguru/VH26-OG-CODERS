import tempfile
from pathlib import Path
import pytest

from core.common.models import Diagnostic, Classification, Span, SourceLocation
from services.ai.models import ReviewMode, AgentStatus
from services.ai.providers import MockLLMProvider, OllamaProvider, OpenAIProvider, get_llm_provider
from services.ai.redactor import SecretRedactor
from services.ai.tracing import LangFuseTracer
from services.ai.orchestrator import AIOrchestrator
from services.ai.agents.resource_hunter import ResourceHunterAgent
from services.ai.agents.code_reviewer import CodeReviewerAgent
from services.ai.agents.root_cause import RootCauseAgent
from services.ai.agents.security_impact import SecurityImpactAgent
from services.ai.agents.fix_generator import FixGeneratorAgent
from services.ai.agents.regression import RegressionAgent
from services.ai.agents.verification import VerificationAgent
from services.ai.agents.pr_agent import PRAgent
from services.ai.agents.documentation import DocumentationAgent
from services.ai.agents.policy_agent import PolicyAgent


def test_secret_redactor_sanitizes_keys():
    raw_code = "api_key = 'sk-1234567890123456789012345' \n db = postgres://user:secretpass123@localhost:5432/db"
    sanitized, redaction_count = SecretRedactor.redact(raw_code)
    assert "secretpass123" not in sanitized
    assert "sk-1234567890123456789012345" not in sanitized
    assert redaction_count >= 2
    assert "[REDACTED_OPENAI_KEY]" in sanitized or "[REDACTED_API_KEY]" in sanitized


def test_llm_provider_factory():
    p_mock = get_llm_provider("mock")
    assert isinstance(p_mock, MockLLMProvider)
    assert p_mock.provider_name == "MockLLM"

    p_ollama = get_llm_provider("ollama")
    assert isinstance(p_ollama, OllamaProvider)

    p_openai = get_llm_provider("openai", api_key="sk-test-key")
    assert isinstance(p_openai, OpenAIProvider)


def test_langfuse_tracer_user_isolation():
    tracer = LangFuseTracer(user_id="user_123", org_id="org_456")
    log_entry = tracer.log_agent_step("TestAgent", AgentStatus.COMPLETED, 15.5, "Success")
    
    assert log_entry.user_id == "user_123"
    assert log_entry.org_id == "org_456"
    assert log_entry.trace_id.startswith("trace_")
    assert len(tracer.logs) == 1


def test_resource_hunter_safe_preservation():
    provider = MockLLMProvider()
    hunter = ResourceHunterAgent(provider=provider)

    span = Span(start=SourceLocation(line=5, column=1), end=SourceLocation(line=5, column=10))
    diag_safe = Diagnostic(
        finding_id="SAFE-001",
        rule_id="RULE-001",
        message="Resource safe",
        classification=Classification.SAFE,
        file_path="safe.py",
        location=span,
        resource_type="FILE",
        reason="Resource is properly closed.",
    )

    res = hunter.run({"diagnostic": diag_safe})
    assert res.status == AgentStatus.COMPLETED
    assert "SAFE" in res.summary or "safe" in res.summary.lower()


def test_code_reviewer_agent():
    provider = MockLLMProvider()
    reviewer = CodeReviewerAgent(provider=provider)
    res = reviewer.run({"diagnostics": [], "target_name": "test_module.py"})
    assert res.status == AgentStatus.COMPLETED
    assert "Zero Resource Leaks" in res.summary


def test_end_to_end_fix_verification_passed():
    """End-to-End Test: Vulnerable code -> Candidate AI Fix -> Isolated Deterministic Verification -> VERIFIED_FIX."""
    provider = MockLLMProvider()
    orchestrator = AIOrchestrator(provider=provider, user_id="u1", org_id="o1")

    vulnerable_code = (
        "import sqlite3\n"
        "def fetch_data():\n"
        "    conn = sqlite3.connect('test.db')\n"
        "    res = conn.execute('SELECT 1').fetchall()\n"
        "    return res\n"
    )

    span = Span(start=SourceLocation(line=3, column=5), end=SourceLocation(line=3, column=35))
    diag_leak = Diagnostic(
        finding_id="LEAK-SQL-01",
        rule_id="RULE_DB_001",
        message="Unclosed sqlite3 connection handle 'conn'",
        classification=Classification.DEFINITE_LEAK,
        file_path="db_service.py",
        location=span,
        resource_type="DATABASE",
        resource_variable="conn",
        reason="Connection 'conn' remains owned at function exit.",
    )

    result = orchestrator.generate_and_verify_fix(diag_leak, source_code=vulnerable_code, file_name="db_service.py")

    assert "verification_status" in result
    assert result["is_verified"] is True
    assert result["verification_status"] == "VERIFIED_FIX"
    assert "✓ PATCH VERIFIED" in result["reason"] or "verified" in result["reason"].lower()


def test_end_to_end_fix_verification_rejected():
    """End-to-End Test: Bad AI Candidate Patch -> Re-analyzed -> REJECTED."""
    class BadPatchProvider(MockLLMProvider):
        def generate(self, prompt: str, system_prompt=None, temperature=0.0) -> str:
            # Generate a bad patch that leaves leak unclosed
            return "```python\nimport sqlite3\ndef fetch_data():\n    conn = sqlite3.connect('test.db')\n    if False:\n        conn.close()\n    return res\n```"

    orchestrator = AIOrchestrator(provider=BadPatchProvider(), user_id="u1", org_id="o1")

    vulnerable_code = (
        "import sqlite3\n"
        "def fetch_data():\n"
        "    conn = sqlite3.connect('test.db')\n"
        "    return conn\n"
    )

    span = Span(start=SourceLocation(line=3, column=5), end=SourceLocation(line=3, column=35))
    diag_leak = Diagnostic(
        finding_id="LEAK-BAD-01",
        rule_id="RULE_DB_001",
        message="Unclosed sqlite3 connection handle 'conn'",
        classification=Classification.DEFINITE_LEAK,
        file_path="db_service.py",
        location=span,
        resource_type="DATABASE",
        resource_variable="conn",
        reason="Connection 'conn' remains unclosed.",
    )

    result = orchestrator.generate_and_verify_fix(diag_leak, source_code=vulnerable_code, file_name="db_service.py")

    assert result["is_verified"] is False
    assert result["verification_status"] == "REJECTED"


def test_ai_review_orchestrator_full_workflow():
    provider = MockLLMProvider()
    orchestrator = AIOrchestrator(provider=provider, user_id="u_test", org_id="o_test")

    span = Span(start=SourceLocation(line=2, column=1), end=SourceLocation(line=2, column=20))
    diag = Diagnostic(
        finding_id="LEAK-999",
        rule_id="RULE_FILE_001",
        message="Unclosed file stream",
        classification=Classification.DEFINITE_LEAK,
        file_path="service.py",
        location=span,
        resource_type="FILE",
        resource_variable="f",
        reason="Unclosed file handle",
    )

    source = "def process():\n    f = open('data.txt')\n    return f.read()\n"

    review_res = orchestrator.review([diag], source_code=source, review_mode=ReviewMode.SENIOR_ENGINEER)

    assert review_res.overall_status == "FAILED"
    assert review_res.new_leaks_count == 1
    assert review_res.user_id == "u_test"
    assert review_res.org_id == "o_test"
    assert len(review_res.activity_timeline) > 0
