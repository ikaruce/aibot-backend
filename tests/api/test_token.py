"""Tests for POST /api/v1/token — on-demand installation token issuance."""

import pytest
import respx
import httpx

from tests.conftest import FAKE_API_KEY, signed_post


def auth_header(key: str = FAKE_API_KEY) -> dict:
    return {"Authorization": f"Bearer {key}"}


@pytest.mark.asyncio
async def test_token_endpoint_returns_token(client, mocker):
    mocker.patch(
        "aibot.api.token.get_repo_installation_id",
        return_value=42,
    )
    mocker.patch(
        "aibot.api.token.get_installation_token",
        return_value=("ghs_fresh_token", "2099-01-01T00:00:00Z"),
    )

    res = client.post(
        "/api/v1/token",
        json={"repo": "owner/myrepo"},
        headers=auth_header(),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token"] == "ghs_fresh_token"
    assert data["expires_at"] == "2099-01-01T00:00:00Z"


def test_token_endpoint_rejects_missing_auth(client):
    res = client.post("/api/v1/token", json={"repo": "owner/repo"})
    assert res.status_code == 401


def test_token_endpoint_rejects_wrong_api_key(client):
    res = client.post(
        "/api/v1/token",
        json={"repo": "owner/repo"},
        headers=auth_header("wrong-key"),
    )
    assert res.status_code == 401


def test_token_endpoint_rejects_malformed_repo(client):
    res = client.post(
        "/api/v1/token",
        json={"repo": "not-a-valid-repo-name"},
        headers=auth_header(),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_token_endpoint_returns_404_when_app_not_installed(client, mocker):
    mocker.patch(
        "aibot.api.token.get_repo_installation_id",
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=None, response=httpx.Response(404)
        ),
    )

    res = client.post(
        "/api/v1/token",
        json={"repo": "owner/uninstalled"},
        headers=auth_header(),
    )
    assert res.status_code == 404
