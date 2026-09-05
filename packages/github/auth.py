"""GitHub Authentication Provider for LeakGuard.

Supports:
- Personal Access Token (PAT) mode for development
- GitHub App JWT mode (stubbed for production)

SECURITY: Tokens are read exclusively from environment variables.
Never hardcode tokens. Never expose to frontend.
"""
import os
import time
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class GitHubAuthProvider:
    """Provides GitHub authentication tokens from environment variables only."""

    def __init__(self) -> None:
        self._pat_token: str = os.getenv("GITHUB_TOKEN", "")
        self._app_id: str = os.getenv("GITHUB_APP_ID", "")
        self._app_private_key: str = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
        self._installation_id: str = os.getenv("GITHUB_INSTALLATION_ID", "")

    @property
    def mode(self) -> str:
        """Returns 'app' if GitHub App credentials are configured, else 'pat'."""
        if self._app_id and self._app_private_key:
            return "app"
        return "pat"

    def get_token(self) -> str:
        if self.mode == "app":
            return self._get_app_installation_token()
        pat_token = os.getenv("GITHUB_TOKEN", "")
        if not pat_token or pat_token == "ghp_your_personal_access_token_here":
            raise RuntimeError(
                "No GitHub authentication configured. "
                "Set GITHUB_TOKEN environment variable for PAT mode, "
                "or GITHUB_APP_ID + GITHUB_APP_PRIVATE_KEY for App mode."
            )
        return pat_token

    def _get_app_installation_token(self) -> str:
        """Generate GitHub App installation token via JWT.

        Production implementation: use PyJWT to sign a JWT with the app private key,
        then exchange it for an installation access token via:
            POST /app/installations/{installation_id}/access_tokens

        For now this is documented as a stub — PAT mode is used for development.
        """
        # TODO: Implement GitHub App JWT exchange for production
        # Example:
        #   import jwt as pyjwt
        #   payload = {"iat": now, "exp": now + 600, "iss": app_id}
        #   jwt_token = pyjwt.encode(payload, private_key, algorithm="RS256")
        #   POST /app/installations/{id}/access_tokens with Authorization: Bearer {jwt_token}
        raise NotImplementedError(
            "GitHub App authentication is not yet implemented. "
            "Set GITHUB_TOKEN for PAT mode instead."
        )

    def get_auth_headers(self) -> dict:
        """Returns Authorization headers for GitHub API requests."""
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def is_configured(self) -> bool:
        """Returns True if any authentication mode is configured."""
        return bool(self._pat_token or (self._app_id and self._app_private_key))


# Singleton instance
_auth_provider: Optional[GitHubAuthProvider] = None


def get_auth_provider() -> GitHubAuthProvider:
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = GitHubAuthProvider()
    return _auth_provider
