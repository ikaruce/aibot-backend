"""Tests for dispatch workflow PR creation logic."""

import base64
import json

import pytest
import respx
import httpx

from tests.conftest import FAKE_APP_NAME, FAKE_AICLI_REPO


def _mock_github_pr_flow(
    mock,
    full_name: str,
    default_branch: str = "main",
    base_sha: str = "abc123",
    file_exists: bool = False,
    branch_exists: bool = False,
):
    """Wire up all GitHub API calls needed for create_dispatch_pr."""
    branch = "add-ai-cli-dispatch-workflow"

    mock.get(f"https://api.github.com/repos/{full_name}").mock(
        return_value=httpx.Response(200, json={"default_branch": default_branch})
    )
    mock.get(
        f"https://api.github.com/repos/{full_name}/git/ref/heads/{default_branch}"
    ).mock(return_value=httpx.Response(200, json={"object": {"sha": base_sha}}))

    if file_exists:
        mock.get(
            f"https://api.github.com/repos/{full_name}/contents/.github/workflows/ai-cli-dispatch.yml"
        ).mock(return_value=httpx.Response(200, json={"sha": "fileshaabc"}))
    else:
        mock.get(
            f"https://api.github.com/repos/{full_name}/contents/.github/workflows/ai-cli-dispatch.yml"
        ).mock(return_value=httpx.Response(404))

    if branch_exists:
        mock.get(
            f"https://api.github.com/repos/{full_name}/git/ref/heads/{branch}"
        ).mock(return_value=httpx.Response(200, json={}))
        mock.patch(
            f"https://api.github.com/repos/{full_name}/git/refs/heads/{branch}"
        ).mock(return_value=httpx.Response(200, json={}))
    else:
        mock.get(
            f"https://api.github.com/repos/{full_name}/git/ref/heads/{branch}"
        ).mock(return_value=httpx.Response(404))
        mock.post(
            f"https://api.github.com/repos/{full_name}/git/refs"
        ).mock(return_value=httpx.Response(201, json={}))

    mock.put(
        f"https://api.github.com/repos/{full_name}/contents/.github/workflows/ai-cli-dispatch.yml"
    ).mock(return_value=httpx.Response(201, json={}))

    mock.post(
        f"https://api.github.com/repos/{full_name}/pulls"
    ).mock(return_value=httpx.Response(201, json={"number": 1, "html_url": "https://github.com/pr/1"}))


@pytest.mark.asyncio
async def test_create_dispatch_pr_new_repo():
    from aibot.github.workflow import create_dispatch_pr

    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/new-repo")
        await create_dispatch_pr("ghs_token", "user/new-repo")
        put_calls = [r for r in mock.calls if r.request.method == "PUT"]
        assert len(put_calls) == 1


@pytest.mark.asyncio
async def test_create_dispatch_pr_commits_rendered_template():
    """The committed file must contain APP_NAME, AICLI_REPO, AIBOT_URL substitutions
    and forward AI_CLI_APP_TOKEN to reusable workflows as AIBOT_API_KEY."""
    from aibot.github.workflow import create_dispatch_pr
    from tests.conftest import FAKE_PUBLIC_URL

    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/myrepo")
        await create_dispatch_pr("ghs_token", "user/myrepo")
        put_call = next(r for r in mock.calls if r.request.method == "PUT")

    body = json.loads(put_call.request.content)
    committed = base64.b64decode(body["content"]).decode()
    assert FAKE_APP_NAME in committed
    assert FAKE_AICLI_REPO in committed
    assert FAKE_PUBLIC_URL in committed
    assert "AIBOT_API_KEY: ${{ secrets.AI_CLI_APP_TOKEN }}" in committed
    # get-token job removed — reusable workflow fetches its own token.
    assert "get-token:" not in committed


@pytest.mark.asyncio
async def test_create_dispatch_pr_existing_workflow_updates_file():
    """When the file already exists, the PUT body must include its sha."""
    from aibot.github.workflow import create_dispatch_pr

    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/existing-repo", file_exists=True)
        await create_dispatch_pr("ghs_token", "user/existing-repo")
        put_call = next(r for r in mock.calls if r.request.method == "PUT")

    body = json.loads(put_call.request.content)
    assert body.get("sha") == "fileshaabc"


@pytest.mark.asyncio
async def test_create_dispatch_pr_resets_existing_branch():
    from aibot.github.workflow import create_dispatch_pr

    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/repo-with-branch", branch_exists=True)
        await create_dispatch_pr("ghs_token", "user/repo-with-branch")
        patch_calls = [r for r in mock.calls if r.request.method == "PATCH"]
        assert len(patch_calls) == 1  # branch reset via PATCH


@pytest.mark.asyncio
async def test_create_dispatch_pr_title_differs_for_new_vs_update():
    """New install → 'add/추가' title, re-install → 'update/업데이트' title."""
    from aibot.github.workflow import create_dispatch_pr

    # New
    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/new", file_exists=False)
        await create_dispatch_pr("ghs_token", "user/new")
        pr_call = next(
            r for r in mock.calls
            if r.request.method == "POST" and "pulls" in str(r.request.url)
        )
    new_title = json.loads(pr_call.request.content)["title"]
    assert "추가" in new_title or "add" in new_title.lower()

    # Update
    async with respx.mock as mock:
        _mock_github_pr_flow(mock, "user/existing", file_exists=True)
        await create_dispatch_pr("ghs_token", "user/existing")
        pr_call = next(
            r for r in mock.calls
            if r.request.method == "POST" and "pulls" in str(r.request.url)
        )
    update_title = json.loads(pr_call.request.content)["title"]
    assert "업데이트" in update_title or "update" in update_title.lower()
