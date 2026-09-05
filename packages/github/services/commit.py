"""GitHub Commit Service — user-controlled commit creation.

SECURITY:
- Only creates commits when explicitly triggered by an authenticated user.
- Never auto-pushes unverified AI patches.
- Never directly overwrites the repository without user approval.
"""
import base64
from typing import Optional

from packages.github.client import GitHubClient, GitHubAPIError


class GitHubCommitService:
    """Creates commits on PR branches via GitHub Contents API.

    This service is ONLY called after:
    1. AI fix has been generated
    2. LeakGuard deterministic analyzer has verified the patch
    3. User has explicitly clicked 'Apply Fix & Commit'
    """

    def __init__(self, client: Optional[GitHubClient] = None) -> None:
        self.client = client or GitHubClient()

    def get_file_sha(
        self, owner: str, repo: str, file_path: str, ref: str
    ) -> Optional[str]:
        """Get the blob SHA of an existing file (required for updates)."""
        try:
            data = self.client.get(
                f"/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"
            )
            return data.get("sha")
        except GitHubAPIError:
            return None

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        new_content: str,
        commit_message: str,
        committer_name: str = "LeakGuard Bot",
        committer_email: str = "leakguard-bot@noreply.leakguard.io",
    ) -> dict:
        """Create or update a file on a branch with a commit.

        Args:
            owner: Repository owner (GitHub username or org)
            repo: Repository name
            branch: Branch name (PR source branch)
            file_path: Path to the file within the repository
            new_content: Full new file content (after applying verified patch)
            commit_message: Conventional commit message (e.g. 'fix(leakguard): ...')
            committer_name: Committer display name
            committer_email: Committer email

        Returns:
            GitHub API response containing commit sha and file info.

        Raises:
            GitHubAPIError: On API errors.
        """
        # Get existing file SHA for update (None if new file)
        file_sha = self.get_file_sha(owner, repo, file_path, branch)

        encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        payload = {
            "message": commit_message,
            "content": encoded,
            "branch": branch,
            "committer": {
                "name": committer_name,
                "email": committer_email,
            },
        }

        if file_sha:
            payload["sha"] = file_sha  # Required for updates

        try:
            return self.client.put(
                f"/repos/{owner}/{repo}/contents/{file_path}",
                body=payload,
            )
        except GitHubAPIError as e:
            if e.status_code == 409:
                # Conflict — SHA mismatch, re-fetch and retry once
                new_sha = self.get_file_sha(owner, repo, file_path, branch)
                if new_sha and new_sha != file_sha:
                    payload["sha"] = new_sha
                    return self.client.put(
                        f"/repos/{owner}/{repo}/contents/{file_path}",
                        body=payload,
                    )
            raise

    def generate_commit_message(
        self,
        resource_type: str,
        finding_summary: str,
        strategy: str,
    ) -> str:
        """Generate a meaningful conventional commit message for a verified fix.

        Examples:
            fix(leakguard): close database connection on exception path
            fix(leakguard): release cursor on all execution paths
            fix(leakguard): make file handle cleanup exception-safe
        """
        resource_map = {
            "DATABASE": "database connection",
            "FILE": "file handle",
            "SOCKET": "network socket",
            "HTTP": "HTTP client session",
            "SUBPROCESS": "subprocess handle",
            "LOCK": "lock",
        }
        strategy_map = {
            "context_manager": "use context manager",
            "context-manager": "use context manager",
            "try_finally": "ensure cleanup on exception path",
            "try-finally": "ensure cleanup on exception path",
            "explicit_close": "add explicit close",
        }

        resource_desc = resource_map.get(resource_type.upper(), resource_type.lower())
        strategy_desc = strategy_map.get(strategy.lower(), "apply resource fix")

        # Truncate finding summary for commit message
        summary_short = finding_summary[:60].rstrip() if finding_summary else resource_desc

        return f"fix(leakguard): {resource_desc} — {strategy_desc}\n\nVerified by LeakGuard deterministic analyzer.\nFinding: {summary_short}"
