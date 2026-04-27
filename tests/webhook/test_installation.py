"""Tests for installation webhook event handlers."""

import pytest
import respx
import httpx

from tests.conftest import signed_post, FAKE_AICLI_REPO, FAKE_APP_NAME


def _make_installation_payload(action: str, repos=None, account_type="User", repo_selection="selected"):
    return {
        "action": action,
        "installation": {
            "id": 42,
            "repository_selection": repo_selection,
            "account": {"type": account_type, "login": "testuser"},
        },
        "repositories": repos or [{"full_name": "testuser/myrepo", "name": "myrepo"}],
    }


@pytest.mark.asyncio
async def test_installation_created_calls_provision(client, mocker):
    mock = mocker.patch(
        "aibot.webhook.handlers.installation.provision_repos",
        return_value=None,
    )
    payload = _make_installation_payload("created")
    res = signed_post(client, payload, event="installation")

    assert res.status_code == 200
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_installation_deleted_returns_200(client, mocker):
    mocker.patch("aibot.webhook.handlers.installation.provision_repos")
    payload = _make_installation_payload("deleted")
    res = signed_post(client, payload, event="installation")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_installation_repositories_added_calls_provision(client, mocker):
    mock = mocker.patch(
        "aibot.webhook.handlers.installation.provision_repos",
        return_value=None,
    )
    payload = {
        "action": "added",
        "installation": {"id": 42},
        "repositories_added": [{"full_name": "testuser/newrepo", "name": "newrepo"}],
    }
    res = signed_post(client, payload, event="installation_repositories")
    assert res.status_code == 200
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_provision_repos_creates_pr_for_each_repo(mocker):
    from aibot.github.workflow import provision_repos

    mock_pr = mocker.patch(
        "aibot.github.workflow.create_dispatch_pr",
        return_value=None,
    )
    mocker.patch(
        "aibot.github.workflow.get_installation_token",
        return_value=("ghs_token", "2099-01-01T00:00:00Z"),
    )

    repos = [
        {"full_name": "user/repo-a"},
        {"full_name": "user/repo-b"},
    ]
    await provision_repos(installation_id=42, repos=repos)

    assert mock_pr.call_count == 2
    called_repos = {call.args[1] for call in mock_pr.call_args_list}
    assert called_repos == {"user/repo-a", "user/repo-b"}


@pytest.mark.asyncio
async def test_provision_repos_continues_on_single_failure(mocker):
    """One failing repo must not stop provisioning of the rest."""
    from aibot.github.workflow import provision_repos

    call_count = 0

    async def flaky_pr(token, full_name):
        nonlocal call_count
        call_count += 1
        if full_name == "user/bad-repo":
            raise Exception("API error")

    mocker.patch("aibot.github.workflow.create_dispatch_pr", side_effect=flaky_pr)
    mocker.patch(
        "aibot.github.workflow.get_installation_token",
        return_value=("ghs_token", "2099-01-01T00:00:00Z"),
    )

    repos = [
        {"full_name": "user/bad-repo"},
        {"full_name": "user/good-repo"},
    ]
    await provision_repos(installation_id=42, repos=repos)
    assert call_count == 2  # both attempted
