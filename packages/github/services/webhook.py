"""GitHub Webhook Service — HMAC-SHA256 signature validation and event parsing."""
import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


SUPPORTED_ACTIONS = {"opened", "synchronize", "reopened"}


@dataclass
class PullRequestWebhookEvent:
    action: str
    pr_number: int
    head_sha: str
    base_sha: str
    head_branch: str
    base_branch: str
    repo_owner: str
    repo_name: str
    repo_full_name: str
    pr_title: str
    pr_author: str
    pr_url: str
    installation_id: Optional[int] = None
    delivery_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class WebhookSignatureError(Exception):
    """Raised when webhook signature validation fails."""


class GitHubWebhookService:
    """Validates GitHub webhook signatures and parses events.

    SECURITY: Always validates HMAC-SHA256 signature before processing payload.
    Never trusts raw payload without valid signature.
    """

    def __init__(self, secret: Optional[str] = None) -> None:
        self._secret = secret if secret is not None else os.getenv("GITHUB_WEBHOOK_SECRET", "")

    def verify_signature(self, payload_bytes: bytes, signature_header: Optional[str]) -> bool:
        """Verifies GitHub webhook HMAC-SHA256 signature.

        Args:
            payload_bytes: Raw request body bytes.
            signature_header: Value of 'X-Hub-Signature-256' header.

        Returns:
            True if signature is valid.

        Raises:
            WebhookSignatureError: If signature is missing, malformed, or invalid.
        """
        if not self._secret:
            # If no secret configured, skip validation (dev mode with warning)
            return True

        if not signature_header:
            raise WebhookSignatureError("Missing X-Hub-Signature-256 header")

        if not signature_header.startswith("sha256="):
            raise WebhookSignatureError(
                f"Invalid signature format. Expected 'sha256=...', got: {signature_header[:20]}"
            )

        expected_sig = signature_header[len("sha256="):]
        computed = hmac.new(
            self._secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed, expected_sig):
            raise WebhookSignatureError("Webhook signature mismatch — payload may be tampered")

        return True

    def parse_pull_request_event(
        self,
        payload: Dict[str, Any],
        delivery_id: Optional[str] = None,
    ) -> Optional[PullRequestWebhookEvent]:
        """Parse a pull_request webhook payload into a typed event.

        Returns None for unsupported actions (e.g. closed, labeled, etc).
        """
        action = payload.get("action", "")
        if action not in SUPPORTED_ACTIONS:
            return None

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        installation = payload.get("installation", {})

        head = pr.get("head", {})
        base = pr.get("base", {})

        return PullRequestWebhookEvent(
            action=action,
            pr_number=pr.get("number", 0),
            head_sha=head.get("sha", ""),
            base_sha=base.get("sha", ""),
            head_branch=head.get("ref", ""),
            base_branch=base.get("ref", ""),
            repo_owner=repo.get("owner", {}).get("login", ""),
            repo_name=repo.get("name", ""),
            repo_full_name=repo.get("full_name", ""),
            pr_title=pr.get("title", ""),
            pr_author=pr.get("user", {}).get("login", ""),
            pr_url=pr.get("html_url", ""),
            installation_id=installation.get("id"),
            delivery_id=delivery_id,
            raw=payload,
        )
