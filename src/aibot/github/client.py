"""Shared GitHub API helpers."""

import logging

import httpx

from aibot.config import get_settings

logger = logging.getLogger(__name__)


async def _get_all_repos(token: str) -> list[dict]:
    """Fetch all repositories accessible to an installation token (paginated)."""
    settings = get_settings()
    repos: list[dict] = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            res = await client.get(
                f"{settings.github_api_url}/installation/repositories",
                headers={"Authorization": f"token {token}"},
                params={"per_page": 100, "page": page},
            )
            res.raise_for_status()
            data = res.json()
            repos.extend(data.get("repositories", []))
            if len(repos) >= data.get("total_count", 0):
                break
            page += 1
    return repos
