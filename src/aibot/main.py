import logging

from fastapi import FastAPI

from aibot.webhook.router import router as webhook_router
from aibot.api.token import router as token_router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="aibot — AI CLI GitHub App")
    app.include_router(webhook_router)
    app.include_router(token_router)
    return app


app = create_app()
