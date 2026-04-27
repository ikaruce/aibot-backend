"""Tests for GitHub Actions repository secret upsert."""

import json
from base64 import b64decode, b64encode

import httpx
import pytest
import respx
from nacl import encoding, public

from tests.conftest import FAKE_API_KEY


# A throwaway keypair generated per test run.
_PRIVATE = public.PrivateKey.generate()
_PUBLIC = _PRIVATE.public_key
_PUBLIC_KEY_B64 = _PUBLIC.encode(encoding.Base64Encoder()).decode()
_KEY_ID = "key-id-xyz"


def _decrypt(encrypted_b64: str) -> str:
    sealed = b64decode(encrypted_b64)
    return public.SealedBox(_PRIVATE).decrypt(sealed).decode()


def _mock_secret_flow(mock, full_name: str, name: str = "AI_CLI_APP_TOKEN"):
    mock.get(
        f"https://api.github.com/repos/{full_name}/actions/secrets/public-key"
    ).mock(
        return_value=httpx.Response(
            200, json={"key": _PUBLIC_KEY_B64, "key_id": _KEY_ID}
        )
    )
    mock.put(
        f"https://api.github.com/repos/{full_name}/actions/secrets/{name}"
    ).mock(return_value=httpx.Response(201, json={}))


@pytest.mark.asyncio
async def test_upsert_repo_secret_encrypts_and_puts():
    from aibot.github.secrets import upsert_repo_secret

    async with respx.mock as mock:
        _mock_secret_flow(mock, "user/repo")
        await upsert_repo_secret("ghs_token", "user/repo", "AI_CLI_APP_TOKEN", "plaintext-secret")

        put_call = next(r for r in mock.calls if r.request.method == "PUT")
        body = json.loads(put_call.request.content)
        assert body["key_id"] == _KEY_ID
        assert _decrypt(body["encrypted_value"]) == "plaintext-secret"


@pytest.mark.asyncio
async def test_upsert_repo_secret_uses_token_auth_header():
    from aibot.github.secrets import upsert_repo_secret

    async with respx.mock as mock:
        _mock_secret_flow(mock, "user/repo")
        await upsert_repo_secret("ghs_token", "user/repo", "AI_CLI_APP_TOKEN", "v")

        for call in mock.calls:
            assert call.request.headers["authorization"] == "token ghs_token"


@pytest.mark.asyncio
async def test_upsert_repo_secret_raises_on_http_error():
    from aibot.github.secrets import upsert_repo_secret

    async with respx.mock as mock:
        mock.get(
            "https://api.github.com/repos/user/repo/actions/secrets/public-key"
        ).mock(return_value=httpx.Response(403, json={"message": "Forbidden"}))

        with pytest.raises(httpx.HTTPStatusError):
            await upsert_repo_secret("ghs_token", "user/repo", "AI_CLI_APP_TOKEN", "v")
