"""GitHub Review Service — post PR reviews and inline comments."""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from packages.github.client import GitHubClient, GitHubAPIError
from services.github_pr.comment_builder import LEAKGUARD_REVIEW_MARKER


@dataclass
class InlineComment:
    """A single inline review comment mapped to a diff position."""
    path: str          # file path relative to repo root
    line: int          # line number in the file (right side of diff)
    body: str          # markdown comment body
    side: str = "RIGHT"


@dataclass
class ReviewResult:
    review_id: int
    state: str         # APPROVED, REQUEST_CHANGES, COMMENTED
    html_url: str
    submitted_at: str


class GitHubReviewService:
    """Service for creating and updating GitHub PR reviews and inline comments.

    SECURITY: Only creates/reads reviews — never approves PRs automatically.
    All LeakGuard reviews are posted as REQUEST_CHANGES or COMMENT.
    """

    def __init__(self, client: Optional[GitHubClient] = None) -> None:
        self.client = client or GitHubClient()

    def list_issue_comments(
        self, owner: str, repo: str, issue_number: int
    ) -> List[Dict[str, Any]]:
        """List all issue/PR comments."""
        return self.client.get_paginated(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        )

    def find_leakguard_summary_comment(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[Dict[str, Any]]:
        """Find the persistent LeakGuard summary comment by marker."""
        comments = self.list_issue_comments(owner, repo, pr_number)
        for comment in reversed(comments):
            body = comment.get("body", "")
            if LEAKGUARD_REVIEW_MARKER in body or "🛡️ LeakGuard Code Review" in body:
                return comment
        return None

    def upsert_summary_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> ReviewResult:
        """Create or update the persistent LeakGuard summary comment.

        Uses <!-- leakguard-review --> marker to avoid duplicate comments.
        """
        if LEAKGUARD_REVIEW_MARKER not in body:
            body = f"{LEAKGUARD_REVIEW_MARKER}\n{body}"

        existing = self.find_leakguard_summary_comment(owner, repo, pr_number)
        if existing:
            comment_id = existing.get("id")
            data = self.client.patch(
                f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
                body={"body": body},
            )
            return ReviewResult(
                review_id=data.get("id", comment_id),
                state="COMMENTED",
                html_url=data.get("html_url", existing.get("html_url", "")),
                submitted_at=data.get("updated_at", data.get("created_at", "")),
            )

        return self.create_issue_comment(owner, repo, pr_number, body)

    def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",  # APPROVE, REQUEST_CHANGES, COMMENT
        comments: Optional[List[InlineComment]] = None,
        commit_id: Optional[str] = None,
    ) -> ReviewResult:
        """Create a PR review with optional inline comments.

        Args:
            event: COMMENT (neutral), REQUEST_CHANGES (blocking), APPROVE (not used by LeakGuard)
        """
        payload: Dict[str, Any] = {
            "body": body,
            "event": event,
        }
        if commit_id:
            payload["commit_id"] = commit_id
        if comments:
            payload["comments"] = [
                {
                    "path": c.path,
                    "line": c.line,
                    "side": c.side,
                    "body": c.body,
                }
                for c in comments
            ]

        try:
            data = self.client.post(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                body=payload,
            )
            return ReviewResult(
                review_id=data.get("id", 0),
                state=data.get("state", event),
                html_url=data.get("html_url", ""),
                submitted_at=data.get("submitted_at", ""),
            )
        except GitHubAPIError as e:
            if e.status_code == 422:
                # Fallback: post as issue comment if review fails (e.g. diff position mismatch)
                return self.create_issue_comment(owner, repo, pr_number, body)
            raise

    def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> ReviewResult:
        """Post a plain comment on a PR (fallback when inline review fails)."""
        data = self.client.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            body={"body": body},
        )
        return ReviewResult(
            review_id=data.get("id", 0),
            state="COMMENTED",
            html_url=data.get("html_url", ""),
            submitted_at=data.get("created_at", ""),
        )

    def dismiss_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_id: int,
        message: str = "LeakGuard: Re-scan triggered",
    ) -> None:
        """Dismiss a previous review (e.g. when re-scan shows issues resolved)."""
        try:
            self.client.put(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/dismissals",
                body={"message": message},
            )
        except GitHubAPIError:
            pass  # Best-effort dismiss

    def list_reviews(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """List all reviews on a pull request."""
        return self.client.get_paginated(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        )

    def get_existing_leakguard_review(
        self, owner: str, repo: str, pr_number: int, bot_login: str = "github-actions[bot]"
    ) -> Optional[Dict[str, Any]]:
        """Find existing LeakGuard review for idempotent updates."""
        reviews = self.list_reviews(owner, repo, pr_number)
        for review in reversed(reviews):
            user = review.get("user", {}).get("login", "")
            body = review.get("body", "")
            if "LeakGuard" in body and user in (bot_login, ""):
                return review
        return None
