"""Tests for GitHub API client — all HTTP calls mocked, no real credentials required."""
import json
import pytest
from unittest.mock import MagicMock, patch, Mock

from packages.github.client import GitHubClient, GitHubAPIError, GitHubRateLimitError
from packages.github.auth import GitHubAuthProvider


class MockAuthProvider:
    def get_auth_headers(self):
        return {"Authorization": "Bearer test_token", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def get_token(self):
        return "test_token"


def _make_mock_response(status: int, body: dict | str):
    resp = MagicMock()
    resp.status = status
    if isinstance(body, dict):
        body_bytes = json.dumps(body).encode()
    else:
        body_bytes = body.encode() if isinstance(body, str) else body
    resp.read.return_value = body_bytes
    resp.headers = {}
    return resp


class TestGitHubClientSuccess:

    def setup_method(self):
        self.client = GitHubClient(auth_provider=MockAuthProvider())

    @patch("urllib.request.urlopen")
    def test_get_request_success(self, mock_urlopen):
        mock_resp = _make_mock_response(200, {"id": 1, "name": "myrepo"})
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = self.client.get("/repos/owner/repo")
        assert result == {"id": 1, "name": "myrepo"}

    @patch("urllib.request.urlopen")
    def test_post_request_success(self, mock_urlopen):
        mock_resp = _make_mock_response(201, {"id": 99, "state": "COMMENTED"})
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = self.client.post("/repos/owner/repo/pulls/1/reviews", body={"body": "test"})
        assert result["id"] == 99

    @patch("urllib.request.urlopen")
    def test_204_returns_empty_dict(self, mock_urlopen):
        mock_resp = _make_mock_response(204, "")
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = self.client.delete("/repos/owner/repo/labels/1")
        assert result == {}


class TestGitHubClientErrors:

    def setup_method(self):
        self.client = GitHubClient(auth_provider=MockAuthProvider())

    def _make_http_error(self, code, message):
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.github.com/test",
            code=code,
            msg=message,
            hdrs=MagicMock(**{"get": Mock(return_value="")}),
            fp=None,
        )
        err.read = Mock(return_value=json.dumps({"message": message}).encode())
        err.headers = MagicMock(**{"get": Mock(return_value="")})
        return err

    @patch("urllib.request.urlopen")
    def test_401_raises_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(401, "Bad credentials")
        with pytest.raises(GitHubAPIError) as exc_info:
            self.client.get("/repos/owner/repo")
        assert exc_info.value.status_code == 401

    @patch("urllib.request.urlopen")
    def test_403_raises_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(403, "Resource not accessible by integration")
        with pytest.raises(GitHubAPIError) as exc_info:
            self.client.get("/repos/owner/private-repo")
        assert exc_info.value.status_code == 403

    @patch("urllib.request.urlopen")
    def test_404_raises_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(404, "Not Found")
        with pytest.raises(GitHubAPIError) as exc_info:
            self.client.get("/repos/owner/nonexistent")
        assert exc_info.value.status_code == 404

    @patch("urllib.request.urlopen")
    def test_409_raises_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(409, "Conflict")
        with pytest.raises(GitHubAPIError) as exc_info:
            self.client.put("/repos/owner/repo/contents/file.py", body={})
        assert exc_info.value.status_code == 409

    @patch("urllib.request.urlopen")
    def test_422_raises_api_error(self, mock_urlopen):
        mock_urlopen.side_effect = self._make_http_error(422, "Validation Failed")
        with pytest.raises(GitHubAPIError) as exc_info:
            self.client.post("/repos/owner/repo/pulls/1/reviews", body={})
        assert exc_info.value.status_code == 422


class TestGitHubAuthProvider:

    def test_no_token_raises_runtime_error(self):
        import os
        original = os.environ.pop("GITHUB_TOKEN", None)
        original_app_id = os.environ.pop("GITHUB_APP_ID", None)
        original_key = os.environ.pop("GITHUB_APP_PRIVATE_KEY", None)
        try:
            auth = GitHubAuthProvider()
            with pytest.raises(RuntimeError, match="No GitHub authentication configured"):
                auth.get_token()
        finally:
            if original:
                os.environ["GITHUB_TOKEN"] = original
            if original_app_id:
                os.environ["GITHUB_APP_ID"] = original_app_id
            if original_key:
                os.environ["GITHUB_APP_PRIVATE_KEY"] = original_key

    def test_pat_mode_returns_token(self):
        import os
        os.environ["GITHUB_TOKEN"] = "test_pat_token_xyz"
        try:
            auth = GitHubAuthProvider()
            assert auth.mode == "pat"
            assert auth.get_token() == "test_pat_token_xyz"
        finally:
            del os.environ["GITHUB_TOKEN"]

    def test_auth_headers_contain_token(self):
        import os
        os.environ["GITHUB_TOKEN"] = "test_header_token"
        try:
            auth = GitHubAuthProvider()
            headers = auth.get_auth_headers()
            assert "Authorization" in headers
            assert "Bearer test_header_token" in headers["Authorization"]
        finally:
            del os.environ["GITHUB_TOKEN"]

    def test_app_mode_detected_when_env_set(self):
        import os
        os.environ["GITHUB_APP_ID"] = "12345"
        os.environ["GITHUB_APP_PRIVATE_KEY"] = "-----BEGIN RSA PRIVATE KEY-----"
        try:
            auth = GitHubAuthProvider()
            assert auth.mode == "app"
        finally:
            del os.environ["GITHUB_APP_ID"]
            del os.environ["GITHUB_APP_PRIVATE_KEY"]
