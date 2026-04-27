"""Dispatch workflow PR creation logic."""

import base64
import logging
from pathlib import Path

import httpx

from aibot.config import get_settings
from aibot.github.auth import get_installation_token
from aibot.github.secrets import upsert_repo_secret

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
_WORKFLOW_PATH = ".github/workflows/ai-cli-dispatch.yml"
_BRANCH = "add-ai-cli-dispatch-workflow"


def _render_dispatch() -> str:
    settings = get_settings()
    template = (_TEMPLATES_DIR / "dispatch.yml").read_text()
    return (
        template
        .replace("{{APP_NAME}}", settings.app_name)
        .replace("{{AICLI_REPO}}", settings.aicli_repo)
        .replace("{{AIBOT_URL}}", settings.public_url)
    )


def _render_pr_body(existing: bool = False) -> str:
    settings = get_settings()
    body = (_TEMPLATES_DIR / "pr_body.md").read_text()
    body = body.replace("{{APP_NAME}}", settings.app_name)
    if existing:
        body = (
            "> **기존 파일을 변경합니다.** "
            f"`{_WORKFLOW_PATH}`이 이미 존재하므로 최신 버전으로 업데이트합니다.\n\n"
            + body
        )
    return body


async def create_dispatch_pr(token: str, full_name: str) -> None:
    """Create (or update) the dispatch workflow PR in a user repository."""
    settings = get_settings()
    base_url = settings.github_api_url
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    workflow_content = _render_dispatch()

    async with httpx.AsyncClient() as client:
        # ── Resolve default branch and its SHA ────────────────────────────
        repo_res = await client.get(f"{base_url}/repos/{full_name}", headers=headers)
        repo_res.raise_for_status()
        default_branch = repo_res.json()["default_branch"]

        ref_res = await client.get(
            f"{base_url}/repos/{full_name}/git/ref/heads/{default_branch}",
            headers=headers,
        )
        ref_res.raise_for_status()
        base_sha = ref_res.json()["object"]["sha"]

        # ── Check whether workflow file already exists ────────────────────
        file_res = await client.get(
            f"{base_url}/repos/{full_name}/contents/{_WORKFLOW_PATH}",
            headers=headers,
            params={"ref": default_branch},
        )
        existing = file_res.status_code == 200
        existing_file_sha = file_res.json().get("sha") if existing else None

        # ── Create or reset the feature branch ───────────────────────────
        branch_res = await client.get(
            f"{base_url}/repos/{full_name}/git/ref/heads/{_BRANCH}",
            headers=headers,
        )
        if branch_res.status_code == 200:
            await client.patch(
                f"{base_url}/repos/{full_name}/git/refs/heads/{_BRANCH}",
                headers=headers,
                json={"sha": base_sha, "force": True},
            )
        else:
            await client.post(
                f"{base_url}/repos/{full_name}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{_BRANCH}", "sha": base_sha},
            )

        # ── Commit workflow file to feature branch ────────────────────────
        file_body: dict = {
            "message": f"chore: add {settings.app_name} dispatch workflow",
            "content": base64.b64encode(workflow_content.encode()).decode(),
            "branch": _BRANCH,
        }
        if existing_file_sha:
            file_body["sha"] = existing_file_sha

        put_res = await client.put(
            f"{base_url}/repos/{full_name}/contents/{_WORKFLOW_PATH}",
            headers=headers,
            json=file_body,
        )
        put_res.raise_for_status()

        # ── Open the PR ───────────────────────────────────────────────────
        pr_title = (
            f"chore: {settings.app_name} dispatch workflow 업데이트"
            if existing
            else f"chore: {settings.app_name} dispatch workflow 추가"
        )
        pr_res = await client.post(
            f"{base_url}/repos/{full_name}/pulls",
            headers=headers,
            json={
                "title": pr_title,
                "body": _render_pr_body(existing=existing),
                "head": _BRANCH,
                "base": default_branch,
            },
        )
        pr_res.raise_for_status()

    logger.info("PR created for %s (update=%s)", full_name, existing)


async def provision_repos(
    installation_id: int,
    repos: list[dict],
    token: str | None = None,
) -> None:
    """Provision dispatch workflow PRs for a list of repositories."""
    if token is None:
        token, _ = await get_installation_token(installation_id)

    api_key = get_settings().api_key
    for repo in repos:
        full_name = repo["full_name"]
        try:
            await upsert_repo_secret(token, full_name, "AI_CLI_APP_TOKEN", api_key)
        except Exception as exc:
            # Missing `secrets: write` permission etc. — log and continue so the
            # workflow PR is still opened; the user can set the secret manually.
            logger.error("Failed to set AI_CLI_APP_TOKEN on %s: %s", full_name, exc)
        try:
            await create_dispatch_pr(token, full_name)
        except Exception as exc:
            logger.error("Failed to provision %s: %s", full_name, exc)
