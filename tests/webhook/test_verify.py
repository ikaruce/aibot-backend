"""Tests for webhook HMAC signature verification."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FAKE_WEBHOOK_SECRET, make_signature, signed_post


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_webhook_accepts_valid_signature(client, mocker):
    mocker.patch("aibot.webhook.router.handle_installation")
    payload = {"action": "created", "installation": {"id": 1}}
    res = signed_post(client, payload, event="installation")
    assert res.status_code == 200


def test_webhook_rejects_missing_signature(client):
    body = json.dumps({"foo": "bar"}).encode()
    res = client.post(
        "/webhook",
        content=body,
        headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
    )
    assert res.status_code == 401


def test_webhook_rejects_wrong_signature(client):
    body = json.dumps({"foo": "bar"}).encode()
    res = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=deadbeef",
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json",
        },
    )
    assert res.status_code == 401


def test_webhook_rejects_tampered_body(client):
    payload = {"action": "created"}
    body = json.dumps(payload).encode()
    sig = make_signature(b"different body")  # sign different content
    res = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json",
        },
    )
    assert res.status_code == 401


def test_webhook_unknown_event_returns_200(client):
    res = signed_post(client, {"foo": "bar"}, event="unknown_event")
    assert res.status_code == 200
