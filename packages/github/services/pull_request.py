"""GitHub Pull Request Service — fetch PR metadata, files, and diffs."""
import base64
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from packages.github.client import GitHubClient


@dataclass
class PRFile:
    filename: str
    status: str          # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: str           # unified diff patch for this file
    raw_url: str
    blob_url: str
    sha: str
    previous_filename: Optional[str] = None
    content: Optional[str] = None  # populated on-demand via get_file_content


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    head_sha: str
    base_sha: str
    head_branch: str
    base_branch: str
    author: str
    repo_owner: str
    repo_name: str
    url: str
    draft: bool = False
    mergeable: Optional[bool] = None
    body: Optional[str] = None


class GitHubPullRequestService:
    """Service for interacting with GitHub Pull Request API."""

    def __init__(self, client: Optional[GitHubClient] = None) -> None:
        self.client = client or GitHubClient()

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        """Fetch pull request metadata."""
        data = self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return PullRequest(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            head_sha=data["head"]["sha"],
            base_sha=data["base"]["sha"],
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            author=data["user"]["login"],
            repo_owner=owner,
            repo_name=repo,
            url=data["html_url"],
            draft=data.get("draft", False),
            mergeable=data.get("mergeable"),
            body=data.get("body"),
        )

    def get_pull_request_files(
        self, owner: str, repo: str, pr_number: int
    ) -> List[PRFile]:
        """Fetch list of files changed in a pull request."""
        data = self.client.get_paginated(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        )
        files = []
        for f in data:
            files.append(
                PRFile(
                    filename=f["filename"],
                    status=f["status"],
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                    changes=f.get("changes", 0),
                    patch=f.get("patch", ""),
                    raw_url=f.get("raw_url", ""),
                    blob_url=f.get("blob_url", ""),
                    sha=f.get("sha", ""),
                    previous_filename=f.get("previous_filename"),
                )
            )
        return files

    def get_python_files_only(self, owner: str, repo: str, pr_number: int) -> List[PRFile]:
        """Returns only Python files changed in the PR (added or modified)."""
        files = self.get_pull_request_files(owner, repo, pr_number)
        return [
            f for f in files
            if f.filename.endswith(".py") and f.status in ("added", "modified")
        ]

    def get_file_content(
        self, owner: str, repo: str, file_path: str, ref: str
    ) -> str:
        """Fetch raw file content at a specific git ref (commit SHA or branch)."""
        try:
            data = self.client.get(
                f"/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"
            )
            if isinstance(data, dict) and data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return ""
        except Exception:
            return ""

    def get_pull_request_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the full unified diff for the pull request."""
        return self.client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            extra_headers={"Accept": "application/vnd.github.diff"},
        )
