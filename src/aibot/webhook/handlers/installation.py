"""Handlers for GitHub App installation webhook events."""

import logging

from aibot.github.workflow import provision_repos

logger = logging.getLogger(__name__)


async def handle_installation(payload: dict) -> None:
    action = payload.get("action")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")

    if action == "created":
        logger.info("Installation created: id=%s", installation_id)
        repo_selection = installation.get("repository_selection", "selected")
        if repo_selection == "all":
            from aibot.github.auth import get_installation_token
            from aibot.github.client import _get_all_repos
            token, _ = await get_installation_token(installation_id)
            repos = await _get_all_repos(token)
        else:
            repos = payload.get("repositories", [])
        await provision_repos(installation_id, repos)

    elif action == "deleted":
        logger.info("Installation deleted: id=%s", installation_id)


async def handle_installation_repositories(payload: dict) -> None:
    action = payload.get("action")
    installation_id = payload["installation"]["id"]

    if action == "added":
        repos = payload.get("repositories_added", [])
        logger.info(
            "Repos added to installation %s: %s",
            installation_id,
            [r["full_name"] for r in repos],
        )
        await provision_repos(installation_id, repos)
