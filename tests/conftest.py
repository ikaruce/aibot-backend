"""Shared fixtures for aibot tests."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

# ── Fake app credentials ──────────────────────────────────────────────────────

FAKE_APP_ID = "12345"
FAKE_WEBHOOK_SECRET = "test-webhook-secret"
FAKE_API_KEY = "test-api-key-abc123"
FAKE_AICLI_REPO = "ikaruce/ai-cli-workflow"
FAKE_APP_NAME = "aibot"
FAKE_PUBLIC_URL = "https://aibot.example.com"

# Minimal RSA private key for tests (generated with cryptography library, not used in production)
FAKE_PRIVATE_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAi9ZENeKvXrUXJmc0QZy9FtwhipMyyXF4LooxQKE193TH0DQw\n"
    "tLd5yyqv6dh3C9MsBEMSEjM3wABfOpL+XGCS4GmDIBFG5tabQChr94iIlWISFnG7\n"
    "gSu5q4niovIkawLpqkJ3waGQaUzGyryxCe7ehptg7k/Jnd6YBLTIm6fpORNgIMZ8\n"
    "VJo/mYtBJhf8HpVxxyqlWNH+YoawDKFaSP6ZX6xR3OBWuClgkk2yvm6B6w7/s4s8\n"
    "/AT8JCHU1LPfIlAEkEU4H5yozMV1oMjAjMRDK7OyipSfPfeJ4nbAfHyyacE49B8u\n"
    "KjNG9MaxPjo89FsfvyxVhjYOWN3oRk5cisAdMQIDAQABAoIBABTFXZm+HjEsfPp7\n"
    "V0vCWGP44WflYs8r8koXb3wbdhoCWAZueihIcz2LuFg9NbxP6w3cWJF+LMhxmwjm\n"
    "+gQGuZ++jHegRAPYhMm24ggBWShh9Nst8Z1yPUC5roG9rfh8lPDGsWXVoHnDqb5G\n"
    "NkCKIWD6hh9f7UwXMEV4BQRPS1lAIJolTyLnDtqzDLqs3e6qR9gLfbOKrkzAX3YE\n"
    "H/YevkhWxaX2NceIwMeDUASVP1YSL5JJ3kLWJHOlk9WYamoZLKzf96TB8ju8oO+f\n"
    "/VDXuZiioSvaF1E48i85nDPQCbsp4O3+ESyG6WDrBy9/HDOCT1898G/843VPxp2D\n"
    "CBIkbPECgYEAxP6SQknFENoFvJhxttq4WJgNYo9pjnMEeop31FY3le+yHvvM6+KF\n"
    "/vCrEy90xG2dt0AqASzQWTQWx4fbRRu5e5EM74f5QhYQfnrpRb5qpa5D/FcYfK8e\n"
    "KpK4y9avuXh4JbJPjSPfKWURbSOwDPamY3ez4VZggh+42HWyrMbe3VcCgYEAtbjk\n"
    "fkVL3LAdE/0TMo2qyT9vuEaKS5/g+weOLJUEHmzvIvDkrymwfKiTUBJlY0n/xhJJ\n"
    "IWNN1LdTrrhYRK9KTcplpHCtAAm7iinPkjTrRpe6a4Uz4/zEUIuQ6fNs5HOFsqj1\n"
    "se1lYwbp9sq+nZn0MfJ6CkdlrJBwPYEKV028vLcCgYAdAacjn50m2BOUK5ZC6H3Q\n"
    "fcMqyhcu5Hy6Vn1ChNd2em7t5QHNkfNNEL7/+jLlYYahnw8QUTr0h5j7FGQTDvwG\n"
    "19rhwlHPi1Qua4bBwEIP11MnauOuKFL2zdfsG9aQJs76LgFMtQV9IOap/WFE52Sk\n"
    "rNGN0pwvTOB47wu6KSZTzQKBgA8DFS0xQFEc42oRUBKvDVrOuMX6XdZdgNJ8D0yz\n"
    "isGQsjiqudmWkhPaQUEuI94N8OlF/XCaqYVXF7ypUfFqobLHc5ogDMqiAzIovhMP\n"
    "+Be+1RGo0V6WNQmKXhBVobtFp9fYiWOHfwatPYq7uP+ABmJR668JsuaMkBkkndwU\n"
    "efEFAoGBAMBoSCGTRHz2eTsD+rCShysLT0ey0Rgt1JnX5opwutED64c4mr2DIoFw\n"
    "ya5JwvMLBWDG6MxoLBtSDNDs5abSNKD314u/QmLaYOzyoeDVruZzGsJrhO9+A3LE\n"
    "Xf+pSCP7GJOG//j/Qz7GNklA7+X2xD0SQx3/POMlnUCiFF9TE/HN\n"
    "-----END RSA PRIVATE KEY-----\n"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_signature(body: bytes, secret: str = FAKE_WEBHOOK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def signed_post(client: TestClient, payload: dict, event: str = "ping") -> tuple:
    body = json.dumps(payload).encode()
    sig = make_signature(body)
    return client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": event,
            "Content-Type": "application/json",
        },
    )


# ── Environment override fixture ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def env_settings(monkeypatch):
    """Override env vars so Settings() always succeeds in tests.

    Also clears the lru_cache so each test gets a fresh Settings instance
    built from the monkeypatched environment.
    """
    from aibot.config import get_settings
    get_settings.cache_clear()

    monkeypatch.setenv("GITHUB_APP_ID", FAKE_APP_ID)
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", FAKE_PRIVATE_KEY)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", FAKE_WEBHOOK_SECRET)
    monkeypatch.setenv("API_KEY", FAKE_API_KEY)
    monkeypatch.setenv("PUBLIC_URL", FAKE_PUBLIC_URL)
    monkeypatch.setenv("AICLI_REPO", FAKE_AICLI_REPO)
    monkeypatch.setenv("APP_NAME", FAKE_APP_NAME)

    yield

    get_settings.cache_clear()


@pytest.fixture
def client(env_settings):
    from aibot.main import create_app
    return TestClient(create_app())
