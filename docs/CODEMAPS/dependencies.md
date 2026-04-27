<!-- Generated: 2026-04-27 | Files scanned: 7 | Token estimate: ~600 -->

# Dependencies & Integrations Codemap

**Last Updated:** 2026-04-27  
**Package Manager:** uv  
**Python Version:** ≥3.11

## External Services

### GitHub (Primary Integration)

**Authority:** GitHub App + GitHub REST API v3

| Service | Endpoint | Auth Method | Purpose |
|---------|----------|-------------|---------|
| **GitHub App** | https://github.com | RS256 JWT (private key) | Identify as app, mint installation tokens |
| **GitHub REST API** | https://api.github.com | Installation token (OAuth) | Manage repos, create PRs, list files |
| **GitHub Webhooks** | POST /webhook (inbound) | HMAC-SHA256 (webhook secret) | Receive installation/repo events |

**Config Keys:**
- `github_app_id` — App ID for JWT `iss` claim
- `github_private_key` — RS256 private key for JWT signing
- `github_webhook_secret` — HMAC-SHA256 key for webhook verification
- `github_base_url` — Domain override (default: https://github.com)
- `github_api_url` — Computed API URL

**Flows:**
1. **App Authentication:** `generate_jwt()` → RS256 signed JWT (10 min TTL)
2. **Token Exchange:** JWT → Installation token (via `/app/installations/{id}/access_tokens`)
3. **Webhook Verification:** HMAC-SHA256 signature validation on inbound POST
4. **API Operations:** All repo/PR/file operations use installation tokens

---

## Production Dependencies

From `pyproject.toml`:

| Package | Version | Import | Purpose |
|---------|---------|--------|---------|
| **fastapi** | ≥0.136.1 | `from fastapi import FastAPI, APIRouter, ...` | Web framework, routing, request handling |
| **uvicorn[standard]** | ≥0.46.0 | (CLI only) | ASGI server, runs app on port 8000 |
| **httpx** | ≥0.28.1 | `import httpx` | Async HTTP client for GitHub API calls |
| **pyjwt[crypto]** | ≥2.12.1 | `import jwt` | RS256 JWT signing for GitHub App auth |
| **pydantic-settings** | ≥2.14.0 | `from pydantic_settings import BaseSettings` | Environment variable config loading |
| **pydantic** | (transitive) | `from pydantic import BaseModel, field_validator` | Data validation (request/response models) |

### Usage by Module

```
src/aibot/
├─ main.py
│  └─ fastapi.FastAPI()
├─ config.py
│  └─ pydantic_settings.BaseSettings()
├─ github/
│  ├─ auth.py
│  │  ├─ httpx.AsyncClient()
│  │  └─ jwt.encode(..., algorithm="RS256")
│  ├─ client.py
│  │  └─ httpx.AsyncClient()
│  └─ workflow.py
│     ├─ httpx.AsyncClient()
│     └─ base64.b64encode()
├─ webhook/
│  ├─ verify.py
│  │  └─ hmac, hashlib (stdlib)
│  └─ router.py
│     └─ fastapi.APIRouter()
├─ api/
│  └─ token.py
│     ├─ fastapi.APIRouter()
│     ├─ pydantic.BaseModel()
│     ├─ httpx (indirectly via auth.py)
│     └─ re (stdlib)
└─ webhook/
   └─ handlers/
      └─ installation.py
         └─ (imports from above modules)
```

---

## Development Dependencies

From `[dependency-groups] dev`:

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | ≥9.0.3 | Test runner |
| **pytest-asyncio** | ≥1.3.0 | Async test fixture support (`asyncio_mode = "auto"`) |
| **pytest-mock** | ≥3.15.1 | Monkeypatch fixtures |
| **respx** | ≥0.23.1 | Mock httpx requests (HTTP mocking) |

**Test Configuration** (`pyproject.toml`):
```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"          # Auto-fixture async test functions
testpaths = ["tests"]          # Test discovery path
```

**Test Files:**
- `tests/github/test_auth.py` — JWT generation, token exchange
- `tests/github/test_workflow.py` — PR creation, workflow provisioning
- `tests/api/test_token.py` — Token API auth and issuance
- `tests/webhook/test_verify.py` — HMAC-SHA256 signature validation
- `tests/webhook/test_installation.py` — Installation webhook handlers

---

## Environment Variables

**Source:** `.env` file (via `pydantic_settings`)

| Variable | Type | Required | Purpose | Default |
|----------|------|----------|---------|---------|
| `GITHUB_APP_ID` | string | Yes | GitHub App ID | — |
| `GITHUB_PRIVATE_KEY` | string (PEM) | Yes | RS256 private key | — |
| `GITHUB_WEBHOOK_SECRET` | string | Yes | HMAC-SHA256 secret | — |
| `API_KEY` | string | Yes | Static bearer token for `/api/v1/token` | — |
| `GITHUB_BASE_URL` | URL | No | GitHub domain override | `https://github.com` |
| `AICLI_REPO` | string | No | Source of dispatch workflow | `ikaruce/ai-cli-workflow` |
| `APP_NAME` | string | No | App name for PR titles/templates | `aibot` |

**Example .env:**
```bash
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=super-secret-webhook-key
API_KEY=your-api-key-for-actions
```

---

## HTTP Client Configuration

**httpx Usage:**
- **Concurrency:** `async with httpx.AsyncClient()` (per-request client)
- **Headers:** JSON API (Accept: `application/vnd.github+json`)
- **Auth:** Bearer tokens in `Authorization: Bearer {jwt}` or `Authorization: token {token}`
- **Error Handling:** `response.raise_for_status()` for 4xx/5xx

**Timeouts:** None set explicitly (uses httpx defaults: 5s connect, 5s read)

---

## Docker & Deployment

**Dockerfile** (multistage):
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY templates/ templates/

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "aibot.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Port:** 8000 (standard FastAPI)

**Dependencies in Container:**
- python:3.11-slim base
- uv package manager (installed from ghcr.io)
- Production packages only (no dev dependencies)

---

## Dependency Graph

```
┌─────────────────┐
│  fastapi        │ ──┬─── pydantic (models, validation)
│                 │   └─── starlette (ASGI framework)
├─────────────────┤
│  uvicorn        │ ──┬─── h11 (HTTP/1.1 state machine)
│  [standard]     │   └─── (uvloop optional)
├─────────────────┤
│  httpx          │ ──┬─── h11, anyio (async I/O)
│                 │   └─── certifi (SSL certs)
├─────────────────┤
│  pyjwt[crypto]  │ ──┬─── cryptography (RSA signing)
│                 │   └─── (optional: PyJWT[crypto])
├─────────────────┤
│ pydantic-       │ ──┬─── pydantic
│ settings        │   └─── python-dotenv (optional .env)
└─────────────────┘

Testing stack:
├─ pytest
├─ pytest-asyncio ──→ asyncio
├─ pytest-mock ────→ unittest.mock
└─ respx ──────────→ httpx (mocking)
```

---

## Security Notes

- **Private Key:** Stored in environment variable (set via GitHub Secrets in CI/CD)
- **Webhook Secret:** Verified via HMAC-SHA256 constant-time comparison
- **API Key:** Static bearer token, should be rotated periodically
- **No Session Storage:** Stateless design (no database)
- **JWT TTL:** Short-lived (10 min), tied to JWT expiry; installation tokens expire in ~1 hour

See `.env.example` for required secrets format.
