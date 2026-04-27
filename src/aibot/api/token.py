"""POST /api/v1/token — issue a GitHub installation token on demand.

GitHub Actions workflows call this endpoint instead of storing long-lived
credentials. The app generates a fresh installation token (~1 hour TTL) and
returns it to the caller.

Authentication: Bearer token matching the configured API_KEY setting.
"""

import logging
import re

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, field_validator

from aibot.config import get_settings
from aibot.github.auth import get_installation_token, get_repo_installation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")

_REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")


class TokenRequest(BaseModel):
    repo: str

    @field_validator("repo")
    @classmethod
    def repo_must_be_owner_slash_name(cls, v: str) -> str:
        if not _REPO_RE.match(v):
            raise ValueError("repo must be in 'owner/name' format")
        return v


class TokenResponse(BaseModel):
    token: str
    expires_at: str


def _verify_api_key(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    key = authorization.removeprefix("Bearer ").strip()
    if key != get_settings().api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    body: TokenRequest,
    authorization: str | None = Header(default=None),
) -> TokenResponse:
    _verify_api_key(authorization)

    try:
        installation_id = await get_repo_installation_id(body.repo)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"App is not installed on repository: {body.repo}",
            ) from exc
        raise

    token, expires_at = await get_installation_token(installation_id)
    logger.info("Token issued for %s (installation=%s)", body.repo, installation_id)
    return TokenResponse(token=token, expires_at=expires_at)
