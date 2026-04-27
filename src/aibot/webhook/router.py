"""Webhook receiver endpoint."""

import logging

from fastapi import APIRouter, Header, Request

from aibot.webhook.verify import verify_signature
from aibot.webhook.handlers.installation import (
    handle_installation,
    handle_installation_repositories,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    body = await request.body()
    verify_signature(body, x_hub_signature_256)

    payload = await request.json()

    match x_github_event:
        case "installation":
            await handle_installation(payload)
        case "installation_repositories":
            await handle_installation_repositories(payload)
        case _:
            logger.debug("Unhandled event: %s", x_github_event)

    return {"status": "ok"}
