"""Tests for GitHub Review Service — summary comment upsert and inline reviews."""
import pytest
from unittest.mock import MagicMock, patch

from packages.github.services.review import GitHubReviewService, InlineComment
from services.github_pr.comment_builder import LEAKGUARD_REVIEW_MARKER


class TestGitHubReviewService:

    def setup_method(self):
        self.client = MagicMock()
        self.service = GitHubReviewService(client=self.client)

    def test_find_leakguard_summary_by_marker(self):
        self.client.get_paginated.return_value = [
            {"id": 1, "body": "Some other comment"},
            {"id": 42, "body": f"{LEAKGUARD_REVIEW_MARKER}\n## LeakGuard Code Review"},
        ]
        result = self.service.find_leakguard_summary_comment("owner", "repo", 5)
        assert result is not None
        assert result["id"] == 42

    def test_find_leakguard_summary_none_when_missing(self):
        self.client.get_paginated.return_value = [
            {"id": 1, "body": "Unrelated comment"},
        ]
        result = self.service.find_leakguard_summary_comment("owner", "repo", 5)
        assert result is None

    def test_upsert_creates_new_when_none_exists(self):
        self.client.get_paginated.return_value = []
        self.client.post.return_value = {
            "id": 99,
            "html_url": "https://github.com/owner/repo/issues/5#issuecomment-99",
            "created_at": "2026-01-01T00:00:00Z",
        }
        result = self.service.upsert_summary_comment(
            "owner", "repo", 5, "## LeakGuard Code Review\nStatus: PASS"
        )
        assert result.review_id == 99
        self.client.post.assert_called_once()
        call_body = self.client.post.call_args[1]["body"]
        assert LEAKGUARD_REVIEW_MARKER in call_body["body"]

    def test_upsert_updates_existing_comment(self):
        self.client.get_paginated.return_value = [
            {"id": 42, "body": f"{LEAKGUARD_REVIEW_MARKER}\nOld summary", "html_url": "http://x"},
        ]
        self.client.patch.return_value = {
            "id": 42,
            "html_url": "http://x",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        result = self.service.upsert_summary_comment(
            "owner", "repo", 5, f"{LEAKGUARD_REVIEW_MARKER}\nNew summary"
        )
        assert result.review_id == 42
        self.client.patch.assert_called_once()
        self.client.post.assert_not_called()

    def test_create_review_with_inline_comments(self):
        self.client.post.return_value = {
            "id": 7,
            "state": "CHANGES_REQUESTED",
            "html_url": "https://github.com/owner/repo/pull/5#pullrequestreview-7",
            "submitted_at": "2026-01-01T00:00:00Z",
        }
        comments = [InlineComment(path="app.py", line=42, body="Leak detected")]
        result = self.service.create_review(
            "owner", "repo", 5,
            body="Summary",
            event="REQUEST_CHANGES",
            comments=comments,
            commit_id="abc123",
        )
        assert result.review_id == 7
        payload = self.client.post.call_args[1]["body"]
        assert len(payload["comments"]) == 1
        assert payload["comments"][0]["line"] == 42
