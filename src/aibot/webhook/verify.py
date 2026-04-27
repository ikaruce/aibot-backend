"""GitHub webhook HMAC-SHA256 signature verification."""

import hashlib
import hmac

from fastapi import HTTPException

from aibot.config import get_settings


def verify_signature(body: bytes, signature: str | None) -> None:
    """Raise HTTP 401 if the signature is missing or does not match."""
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    secret = get_settings().github_webhook_secret
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
