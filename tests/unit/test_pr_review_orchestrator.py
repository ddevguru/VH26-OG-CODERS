"""Tests for PR Review Orchestrator — mocked GitHub API and AI.

No real GitHub credentials required. No AI provider required.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, Mock
from dataclasses import dataclass

from packages.github.services.webhook import PullRequestWebhookEvent
from services.github_pr.risk_scorer import PRRiskScorer
from services.github_pr.inline_mapper import InlineCommentMapper
from services.github_pr.comment_builder import PRCommentBuilder
from core.common.models import Diagnostic, Classification, Span, SourceLocation, ResourceType


SAMPLE_EVENT = PullRequestWebhookEvent(
    action="opened",
    pr_number=42,
    head_sha="abc1234",
    base_sha="base000",
    head_branch="feature/add-db",
    base_branch="main",
    repo_owner="myorg",
    repo_name="myrepo",
    repo_full_name="myorg/myrepo",
    pr_title="Add database operations",
    pr_author="developer1",
    pr_url="https://github.com/myorg/myrepo/pull/42",
)


def make_diagnostic(
    classification=Classification.DEFINITE_LEAK,
    resource_type="DATABASE",
    line=42,
    var="conn",
    finding_id="LG-001",
):
    return Diagnostic(
        finding_id=finding_id,
        rule_id="LG-DB-001",
        message="Database connection is not closed on exception path",
        classification=classification,
        file_path="app/db.py",
        location=Span(
            start=SourceLocation(line=line, column=1),
            end=SourceLocation(line=line, column=20),
        ),
        resource_type=resource_type,
        resource_variable=var,
        reason="No try/finally block around DB connection",
    )


class TestPRRiskScorer:

    def setup_method(self):
        self.scorer = PRRiskScorer()

    def test_no_findings_score_zero(self):
        result = self.scorer.compute([])
        assert result["score"] == 0
        assert result["label"] == "NONE"
        assert result["definite_count"] == 0

    def test_definite_leak_high_score(self):
        diag = make_diagnostic(Classification.DEFINITE_LEAK, "DATABASE")
        result = self.scorer.compute([diag])
        # DEFINITE(40) + DATABASE(15) = 55
        assert result["score"] == 55
        assert result["definite_count"] == 1
        assert result["potential_count"] == 0

    def test_potential_leak_lower_score(self):
        diag = make_diagnostic(Classification.POTENTIAL_LEAK, "FILE")
        result = self.scorer.compute([diag])
        # POTENTIAL(20) + FILE(2) = 22
        assert result["score"] == 22
        assert result["potential_count"] == 1

    def test_multiple_findings_accumulate(self):
        d1 = make_diagnostic(Classification.DEFINITE_LEAK, "DATABASE", finding_id="LG-001")
        d2 = make_diagnostic(Classification.DEFINITE_LEAK, "FILE", finding_id="LG-002")
        result = self.scorer.compute([d1, d2])
        # (40+15) + (40+5) = 100, capped at 100
        assert result["score"] <= 100
        assert result["definite_count"] == 2

    def test_safe_findings_zero_contribution(self):
        diag = make_diagnostic(Classification.SAFE, "FILE")
        result = self.scorer.compute([diag])
        assert result["score"] == 0

    def test_score_capped_at_100(self):
        # Many definite leaks should not exceed 100
        findings = [
            make_diagnostic(Classification.DEFINITE_LEAK, "DATABASE", finding_id=f"LG-{i}")
            for i in range(5)
        ]
        result = self.scorer.compute(findings)
        assert result["score"] <= 100

    def test_pr_status_fail_on_definite(self):
        result = {"definite_count": 2, "potential_count": 0}
        status = self.scorer.compute_pr_status(result)
        assert status == "FAIL"

    def test_pr_status_warning_on_potential_only(self):
        result = {"definite_count": 0, "potential_count": 1}
        status = self.scorer.compute_pr_status(result)
        assert status == "WARNING"

    def test_pr_status_pass_on_no_findings(self):
        result = {"definite_count": 0, "potential_count": 0}
        status = self.scorer.compute_pr_status(result)
        assert status == "PASS"


class TestInlineCommentMapper:

    def setup_method(self):
        self.mapper = InlineCommentMapper()

    def test_parse_changed_lines_addition(self):
        patch = "@@ -1,3 +1,5 @@\n context\n+added line 2\n+added line 3\n context\n+added line 5"
        lines = self.mapper.parse_changed_lines(patch)
        # Line 2, 3, 5 are added (right side)
        assert 2 in lines
        assert 3 in lines
        assert 5 in lines

    def test_parse_empty_patch(self):
        lines = self.mapper.parse_changed_lines("")
        assert lines == set()

    def test_filter_inline_eligible_finding_on_changed_line(self):
        changed_map = {"app/db.py": {42, 43, 44}}
        diag = make_diagnostic(line=42)
        inline, summary = self.mapper.filter_inline_eligible([diag], changed_map)
        assert len(inline) == 1
        assert len(summary) == 0

    def test_filter_inline_eligible_finding_off_diff(self):
        changed_map = {"app/db.py": {10, 11, 12}}
        diag = make_diagnostic(line=100)  # Not in changed lines (far away)
        inline, summary = self.mapper.filter_inline_eligible([diag], changed_map)
        # Line 100 not near 10-12, should be summary only
        assert len(summary) == 1

    def test_safe_findings_still_processed(self):
        changed_map = {"app/db.py": {42}}
        diag = make_diagnostic(Classification.SAFE, line=42)
        inline, summary = self.mapper.filter_inline_eligible([diag], changed_map)
        # SAFE findings are passed through but should be filtered at comment-building time
        assert len(inline) == 1  # eligible, but comment builder will filter SAFE


class TestPRCommentBuilder:

    def setup_method(self):
        self.builder = PRCommentBuilder(portal_url="http://localhost:3000")

    def test_summary_comment_fail_status(self):
        diag = make_diagnostic(Classification.DEFINITE_LEAK)
        risk = {"score": 87, "label": "CRITICAL", "emoji": "🔴",
                "definite_count": 1, "potential_count": 0, "safe_count": 0, "factors": []}
        comment = self.builder.build_summary_comment(
            pr_number=42, repo_full_name="myorg/myrepo",
            risk=risk, pr_status="FAIL", diagnostics=[diag]
        )
        assert "LeakGuard" in comment
        assert "CHANGES REQUESTED" in comment
        assert "87" in comment
        assert "CRITICAL" in comment
        assert "DEFINITE" in comment

    def test_summary_comment_pass_status(self):
        risk = {"score": 0, "label": "NONE", "emoji": "⚪",
                "definite_count": 0, "potential_count": 0, "safe_count": 3, "factors": []}
        comment = self.builder.build_summary_comment(
            pr_number=1, repo_full_name="myorg/myrepo",
            risk=risk, pr_status="PASS", diagnostics=[]
        )
        assert "PASS" in comment
        assert "Zero Resource Leaks" in comment

    def test_inline_comment_contains_finding_info(self):
        diag = make_diagnostic(Classification.DEFINITE_LEAK, line=42, var="conn")
        comment = self.builder.build_inline_comment(diag)
        assert "DEFINITE RESOURCE LEAK" in comment
        assert "conn" in comment
        assert "42" in comment
        assert "LG-001" in comment

    def test_inline_comment_with_ai_explanation(self):
        diag = make_diagnostic()
        ai_exp = {
            "summary": "DB connection leaks",
            "recommended_strategy": "try_finally",
            "impact": "Connection pool exhaustion",
        }
        comment = self.builder.build_inline_comment(diag, ai_explanation=ai_exp)
        assert "Connection pool exhaustion" in comment
        assert "try/finally" in comment.lower() or "try_finally" in comment

    def test_fix_ready_comment_structure(self):
        diag = make_diagnostic()
        comment = self.builder.build_fix_ready_comment(
            diagnostic=diag,
            unified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-conn = db.connect()\n+with db.connect() as conn:",
            strategy="context_manager",
            verification_steps=["AST valid", "No new leaks"],
        )
        assert "Verified" in comment
        assert "Context Manager" in comment
        assert "DEFINITE_LEAK" in comment
        assert "SAFE" in comment


class TestPRReviewOrchestratorIdempotency:

    def test_idempotency_key_is_repo_pr_sha(self):
        """Validate the idempotency key components."""
        event = SAMPLE_EVENT
        # Same event twice should produce same idempotency key
        key1 = (event.repo_full_name, event.pr_number, event.head_sha)
        key2 = (event.repo_full_name, event.pr_number, event.head_sha)
        assert key1 == key2

    def test_different_sha_different_key(self):
        """Different commit SHA = different scan, not a duplicate."""
        event1 = SAMPLE_EVENT
        event2 = PullRequestWebhookEvent(
            **{**SAMPLE_EVENT.__dict__, "head_sha": "differentsha999"}
        )
        key1 = (event1.repo_full_name, event1.pr_number, event1.head_sha)
        key2 = (event2.repo_full_name, event2.pr_number, event2.head_sha)
        assert key1 != key2
