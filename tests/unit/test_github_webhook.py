"""Tests for GitHub webhook signature validation and event parsing.

All tests use mocked payloads — no real GitHub credentials required.
"""
import hashlib
import hmac
import json
import pytest

from packages.github.services.webhook import (
    GitHubWebhookService,
    WebhookSignatureError,
    PullRequestWebhookEvent,
)


VALID_SECRET = "test-webhook-secret-1234"

VALID_PR_PAYLOAD = {
    "action": "opened",
    "number": 42,
    "pull_request": {
        "number": 42,
        "title": "Add database connection",
        "state": "open",
        "head": {"sha": "abc1234def5678", "ref": "feature/add-db"},
        "base": {"sha": "base123", "ref": "main"},
        "user": {"login": "developer1"},
        "html_url": "https://github.com/myorg/myrepo/pull/42",
    },
    "repository": {
        "name": "myrepo",
        "full_name": "myorg/myrepo",
        "owner": {"login": "myorg"},
    },
    "installation": {"id": 12345},
}


def _make_signature(secret: str, payload: bytes) -> str:
    """Compute HMAC-SHA256 signature."""
    return "sha256=" + hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()


class TestWebhookSignatureValidation:

    def test_valid_signature_accepted(self):
        service = GitHubWebhookService(secret=VALID_SECRET)
        payload = json.dumps(VALID_PR_PAYLOAD).encode()
        sig = _make_signature(VALID_SECRET, payload)
        assert service.verify_signature(payload, sig) is True

    def test_invalid_signature_rejected(self):
        service = GitHubWebhookService(secret=VALID_SECRET)
        payload = json.dumps(VALID_PR_PAYLOAD).encode()
        bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        with pytest.raises(WebhookSignatureError, match="Webhook signature mismatch"):
            service.verify_signature(payload, bad_sig)

    def test_missing_signature_rejected(self):
        service = GitHubWebhookService(secret=VALID_SECRET)
        payload = json.dumps(VALID_PR_PAYLOAD).encode()
        with pytest.raises(WebhookSignatureError, match="Missing"):
            service.verify_signature(payload, None)

    def test_malformed_signature_rejected(self):
        service = GitHubWebhookService(secret=VALID_SECRET)
        payload = json.dumps(VALID_PR_PAYLOAD).encode()
        with pytest.raises(WebhookSignatureError, match="Invalid signature format"):
            service.verify_signature(payload, "notasha256signature")

    def test_no_secret_configured_allows_all(self):
        """In dev mode without GITHUB_WEBHOOK_SECRET set, signature is skipped."""
        service = GitHubWebhookService(secret="")
        payload = json.dumps(VALID_PR_PAYLOAD).encode()
        # Should not raise
        assert service.verify_signature(payload, None) is True

    def test_tampered_payload_rejected(self):
        service = GitHubWebhookService(secret=VALID_SECRET)
        original_payload = json.dumps(VALID_PR_PAYLOAD).encode()
        sig = _make_signature(VALID_SECRET, original_payload)

        # Tamper with payload
        tampered = json.dumps({**VALID_PR_PAYLOAD, "action": "deleted"}).encode()
        with pytest.raises(WebhookSignatureError):
            service.verify_signature(tampered, sig)


class TestWebhookEventParsing:

    def setup_method(self):
        self.service = GitHubWebhookService(secret=VALID_SECRET)

    def test_parse_opened_event(self):
        event = self.service.parse_pull_request_event(VALID_PR_PAYLOAD, delivery_id="test-123")
        assert event is not None
        assert isinstance(event, PullRequestWebhookEvent)
        assert event.action == "opened"
        assert event.pr_number == 42
        assert event.head_sha == "abc1234def5678"
        assert event.base_sha == "base123"
        assert event.head_branch == "feature/add-db"
        assert event.base_branch == "main"
        assert event.repo_owner == "myorg"
        assert event.repo_name == "myrepo"
        assert event.repo_full_name == "myorg/myrepo"
        assert event.pr_author == "developer1"
        assert event.installation_id == 12345
        assert event.delivery_id == "test-123"

    def test_parse_synchronize_event(self):
        payload = {**VALID_PR_PAYLOAD, "action": "synchronize"}
        event = self.service.parse_pull_request_event(payload)
        assert event is not None
        assert event.action == "synchronize"

    def test_parse_reopened_event(self):
        payload = {**VALID_PR_PAYLOAD, "action": "reopened"}
        event = self.service.parse_pull_request_event(payload)
        assert event is not None
        assert event.action == "reopened"

    def test_unsupported_action_returns_none(self):
        """labeled, assigned, review_requested etc should be ignored."""
        for action in ("labeled", "assigned", "review_requested", "edited"):
            payload = {**VALID_PR_PAYLOAD, "action": action}
            result = self.service.parse_pull_request_event(payload)
            assert result is None, f"Expected None for action='{action}', got {result}"

    def test_closed_pr_returns_none(self):
        payload = {**VALID_PR_PAYLOAD, "action": "closed"}
        result = self.service.parse_pull_request_event(payload)
        assert result is None


class TestWebhookIdempotency:

    def test_different_shas_not_duplicate(self):
        """Different head SHAs = different scans (not duplicates)."""
        svc = GitHubWebhookService(secret="")
        p1 = {**VALID_PR_PAYLOAD, "pull_request": {**VALID_PR_PAYLOAD["pull_request"], "head": {"sha": "sha111", "ref": "main"}}}
        p2 = {**VALID_PR_PAYLOAD, "pull_request": {**VALID_PR_PAYLOAD["pull_request"], "head": {"sha": "sha222", "ref": "main"}}}
        e1 = svc.parse_pull_request_event(p1)
        e2 = svc.parse_pull_request_event(p2)
        assert e1.head_sha != e2.head_sha

    def test_same_sha_is_potential_duplicate(self):
        """Same (repo, pr, sha) would trigger idempotency check in orchestrator."""
        svc = GitHubWebhookService(secret="")
        e1 = svc.parse_pull_request_event(VALID_PR_PAYLOAD)
        e2 = svc.parse_pull_request_event(VALID_PR_PAYLOAD)
        assert e1.head_sha == e2.head_sha
        assert e1.repo_full_name == e2.repo_full_name
        assert e1.pr_number == e2.pr_number
