"""Tests for GitHub App JWT generation and installation token fetching."""

import time

import jwt
import pytest
import respx
import httpx

from tests.conftest import FAKE_APP_ID, FAKE_PRIVATE_KEY


def test_generate_jwt_has_correct_claims():
    from aibot.github.auth import generate_jwt

    before = int(time.time())
    token = generate_jwt()
    after = int(time.time())

    # Decode without verification to inspect claims (signature verified implicitly by jwt.encode)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == FAKE_APP_ID
    assert claims["exp"] - claims["iat"] <= 660  # iat is 60 s in past, exp is 10 min from now
    assert claims["iat"] <= before + 1           # issued around now
    assert claims["exp"] >= before + 500         # expires ~10 min later


def test_generate_jwt_is_rs256_signed():
    from aibot.github.auth import generate_jwt

    token = generate_jwt()
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"


@pytest.mark.asyncio
async def test_get_installation_token_returns_token():
    from aibot.github.auth import get_installation_token

    with respx.mock:
        respx.post(
            "https://api.github.com/app/installations/42/access_tokens"
        ).mock(
            return_value=httpx.Response(
                201,
                json={"token": "ghs_testtoken", "expires_at": "2099-01-01T00:00:00Z"},
            )
        )
        token, expires_at = await get_installation_token(42)

    assert token == "ghs_testtoken"
    assert expires_at == "2099-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_get_installation_token_raises_on_api_error():
    from aibot.github.auth import get_installation_token

    with respx.mock:
        respx.post(
            "https://api.github.com/app/installations/99/access_tokens"
        ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

        with pytest.raises(httpx.HTTPStatusError):
            await get_installation_token(99)


@pytest.mark.asyncio
async def test_get_repo_installation_id_returns_id():
    from aibot.github.auth import get_repo_installation_id

    with respx.mock:
        respx.get(
            "https://api.github.com/repos/owner/repo/installation"
        ).mock(
            return_value=httpx.Response(200, json={"id": 777})
        )
        installation_id = await get_repo_installation_id("owner/repo")

    assert installation_id == 777


@pytest.mark.asyncio
async def test_get_repo_installation_id_raises_when_not_installed():
    from aibot.github.auth import get_repo_installation_id

    with respx.mock:
        respx.get(
            "https://api.github.com/repos/owner/uninstalled/installation"
        ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

        with pytest.raises(httpx.HTTPStatusError):
            await get_repo_installation_id("owner/uninstalled")
