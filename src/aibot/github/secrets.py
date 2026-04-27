"""Set GitHub Actions repository secrets via libsodium sealed box."""

from base64 import b64encode

import httpx
from nacl import encoding, public

from aibot.config import get_settings


def _encrypt(public_key_b64: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode())
    return b64encode(sealed).decode()


async def upsert_repo_secret(
    token: str, full_name: str, name: str, value: str
) -> None:
    """Create or update a repository Actions secret."""
    base = get_settings().github_api_url
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient() as client:
        key_res = await client.get(
            f"{base}/repos/{full_name}/actions/secrets/public-key", headers=headers
        )
        key_res.raise_for_status()
        key = key_res.json()

        put_res = await client.put(
            f"{base}/repos/{full_name}/actions/secrets/{name}",
            headers=headers,
            json={
                "encrypted_value": _encrypt(key["key"], value),
                "key_id": key["key_id"],
            },
        )
        put_res.raise_for_status()
