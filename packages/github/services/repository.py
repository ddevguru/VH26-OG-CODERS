"""GitHub Repository Service — repository metadata and permissions."""
from typing import Any, Dict, Optional

from packages.github.client import GitHubClient


class GitHubRepositoryService:
    """Service for interacting with GitHub Repository API."""

    def __init__(self, client: Optional[GitHubClient] = None) -> None:
        self.client = client or GitHubClient()

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata."""
        return self.client.get(f"/repos/{owner}/{repo}")

    def verify_permissions(self, owner: str, repo: str) -> Dict[str, bool]:
        """Verify that the authenticated token has required permissions."""
        try:
            data = self.get_repository(owner, repo)
            perms = data.get("permissions", {})
            return {
                "push": perms.get("push", False),
                "pull": perms.get("pull", False),
                "admin": perms.get("admin", False),
            }
        except Exception:
            return {"push": False, "pull": False, "admin": False}

    def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch name."""
        data = self.get_repository(owner, repo)
        return data.get("default_branch", "main")

    def get_authenticated_user(self) -> Dict[str, Any]:
        """Get authenticated GitHub user info."""
        return self.client.get("/user")
