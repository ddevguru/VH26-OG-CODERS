"""GitHub REST API HTTP Client for LeakGuard.

Handles:
- Authentication (PAT + App token)
- Rate limiting with exponential backoff
- Graceful error handling for 401, 403, 404, 409, 422
- Network error retries

SECURITY: Never logs tokens. Never exposes tokens to frontend.
"""
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple

from packages.github.auth import GitHubAuthProvider, get_auth_provider


class GitHubAPIError(Exception):
    """Raised when GitHub API returns a non-successful response."""

    def __init__(self, status_code: int, message: str, response_body: str = "") -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"GitHub API Error {status_code}: {message}")


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: int) -> None:
        self.reset_at = reset_at
        super().__init__(429, f"Rate limit exceeded. Resets at {reset_at}")


class GitHubClient:
    """HTTP client for GitHub REST API v3.

    Usage:
        client = GitHubClient()
        pr = client.get("/repos/owner/repo/pulls/42")
    """

    BASE_URL = "https://api.github.com"
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0

    def __init__(
        self,
        auth_provider: Optional[GitHubAuthProvider] = None,
        base_url: str = BASE_URL,
    ) -> None:
        self.auth = auth_provider or get_auth_provider()
        self.base_url = base_url.rstrip("/")

    def _build_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = self.auth.get_auth_headers()
        headers["Content-Type"] = "application/json"
        if extra:
            headers.update(extra)
        return headers

    def _handle_response(self, response, url: str) -> Any:
        """Parse response and raise typed errors for bad status codes."""
        body = response.read().decode("utf-8")
        status = response.status

        if status in (200, 201, 204):
            if not body:
                return {}
            return json.loads(body)

        try:
            error_data = json.loads(body)
            msg = error_data.get("message", body)
        except Exception:
            msg = body

        if status == 401:
            raise GitHubAPIError(401, f"Unauthorized — check GITHUB_TOKEN: {msg}")
        elif status == 403:
            raise GitHubAPIError(403, f"Forbidden — insufficient permissions: {msg}")
        elif status == 404:
            raise GitHubAPIError(404, f"Not found: {url} — {msg}")
        elif status == 409:
            raise GitHubAPIError(409, f"Conflict (e.g. merge conflict or duplicate): {msg}")
        elif status == 422:
            raise GitHubAPIError(422, f"Unprocessable entity (validation error): {msg}")
        elif status == 429:
            reset_at = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
            raise GitHubRateLimitError(reset_at)
        else:
            raise GitHubAPIError(status, f"Unexpected error from GitHub API: {msg}", body)

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        extra_headers: Optional[Dict] = None,
        attempt: int = 0,
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._build_headers(extra_headers)
        data = json.dumps(body).encode("utf-8") if body else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return self._handle_response(resp, url)

        except urllib.error.HTTPError as e:
            # Build a fake response-like object from HTTPError
            status = e.code
            body_bytes = e.read()
            body_str = body_bytes.decode("utf-8", errors="replace")

            try:
                error_data = json.loads(body_str)
                msg = error_data.get("message", body_str)
            except Exception:
                msg = body_str

            if status == 429 and attempt < self.MAX_RETRIES:
                reset_at = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait_secs = max(reset_at - int(time.time()), 10)
                time.sleep(min(wait_secs, 60))
                return self._request(method, path, body, extra_headers, attempt + 1)

            if status in (500, 502, 503, 504) and attempt < self.MAX_RETRIES:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait)
                return self._request(method, path, body, extra_headers, attempt + 1)

            if status == 401:
                raise GitHubAPIError(401, f"Unauthorized — check GITHUB_TOKEN: {msg}")
            elif status == 403:
                raise GitHubAPIError(403, f"Forbidden: {msg}")
            elif status == 404:
                raise GitHubAPIError(404, f"Not found: {url}")
            elif status == 409:
                raise GitHubAPIError(409, f"Conflict: {msg}")
            elif status == 422:
                raise GitHubAPIError(422, f"Validation error: {msg}")
            elif status == 429:
                reset_at = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                raise GitHubRateLimitError(reset_at)
            else:
                raise GitHubAPIError(status, msg, body_str)

        except urllib.error.URLError as e:
            if attempt < self.MAX_RETRIES:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait)
                return self._request(method, path, body, extra_headers, attempt + 1)
            raise GitHubAPIError(0, f"Network error: {e.reason}")

    def get(self, path: str, extra_headers: Optional[Dict] = None) -> Any:
        return self._request("GET", path, extra_headers=extra_headers)

    def post(self, path: str, body: Optional[Dict] = None) -> Any:
        return self._request("POST", path, body=body)

    def put(self, path: str, body: Optional[Dict] = None) -> Any:
        return self._request("PUT", path, body=body)

    def patch(self, path: str, body: Optional[Dict] = None) -> Any:
        return self._request("PATCH", path, body=body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def get_paginated(self, path: str, per_page: int = 100) -> list:
        """Fetch all pages of a paginated GitHub API endpoint."""
        results = []
        sep = "&" if "?" in path else "?"
        page = 1
        while True:
            data = self.get(f"{path}{sep}per_page={per_page}&page={page}")
            if not data:
                break
            if isinstance(data, list):
                results.extend(data)
                if len(data) < per_page:
                    break
            else:
                results.append(data)
                break
            page += 1
        return results
