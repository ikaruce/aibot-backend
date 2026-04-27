"""GitHub App authentication: JWT generation and installation token retrieval."""

import time

import httpx
import jwt

from aibot.config import get_settings


def generate_jwt() -> str:
    """Generate a short-lived RS256 JWT to authenticate as the GitHub App."""
    settings = get_settings()
    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued 60 s in the past (clock skew tolerance)
        "exp": now + 600,  # expires in 10 minutes (GitHub maximum)
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, settings.github_private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> tuple[str, str]:
    """Exchange a JWT for a per-installation access token.

    Returns:
        (token, expires_at) where expires_at is an ISO-8601 string.
    """
    settings = get_settings()
    url = f"{settings.github_api_url}/app/installations/{installation_id}/access_tokens"
    async with httpx.AsyncClient() as client:
        res = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {generate_jwt()}",
                "Accept": "application/vnd.github+json",
            },
        )
        res.raise_for_status()
        data = res.json()
        return data["token"], data["expires_at"]


async def get_repo_installation_id(full_name: str) -> int:
    """Look up the installation ID for a given repository.

    Uses the app JWT (not an installation token) so no prior state is needed.
    """
    settings = get_settings()
    url = f"{settings.github_api_url}/repos/{full_name}/installation"
    async with httpx.AsyncClient() as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {generate_jwt()}",
                "Accept": "application/vnd.github+json",
            },
        )
        res.raise_for_status()
        return res.json()["id"]
