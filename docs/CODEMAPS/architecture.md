<!-- Generated: 2026-04-27 | Files scanned: 14 | Token estimate: ~950 -->

# Architecture Codemap

**Last Updated:** 2026-04-27  
**Framework:** FastAPI (Python 3.11+)  
**Entry Point:** `src/aibot/main.py::create_app()`

## System Overview

A GitHub App backend that provisions AI CLI dispatch workflows to user repositories via pull requests. Exposes REST API endpoints for webhook events and on-demand token issuance.

## GitHub App Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User installs app on GitHub                              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. GitHub sends POST /webhook                               │
│    - Headers: X-Hub-Signature-256, X-GitHub-Event           │
│    - Payload: installation + repositories                   │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Signature verified via HMAC-SHA256                        │
│    - Uses github_webhook_secret from config                 │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Route to handler: installation / installation_repositories
│    - handle_installation(payload)                           │
│    - handle_installation_repositories(payload)              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Provision dispatch workflow PR for each repo              │
│    - create_dispatch_pr(token, full_name)                   │
│    - Commits .github/workflows/ai-cli-dispatch.yml          │
│    - Opens PR with templated body (pr_body.md)              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. GitHub Actions runs dispatch.yml                         │
│    - Calls POST /api/v1/token to get fresh installation token
│    - AI CLI workflows execute with auth context             │
└─────────────────────────────────────────────────────────────┘
```

## Authentication Layers

| Layer | Method | Used By | TTL |
|-------|--------|---------|-----|
| **JWT (App Auth)** | RS256 private key | `generate_jwt()` | 10 min |
| **Installation Token** | OAuth via app JWT | `get_installation_token(installation_id)` | ~1 hour |
| **API Key** | Bearer token (static) | `POST /api/v1/token` auth | Configured |

## Configuration

**Source:** `src/aibot/config.py::Settings` (Pydantic BaseSettings)

| Setting | Purpose | Required |
|---------|---------|----------|
| `github_app_id` | App identity for JWT `iss` | Yes |
| `github_private_key` | RS256 private key for JWT signing | Yes |
| `github_webhook_secret` | HMAC-SHA256 secret for webhook verification | Yes |
| `github_base_url` | GitHub domain (default: https://github.com) | No |
| `github_api_url` | Derived: `/api/v3` or `/api/github.com` | Computed |
| `aicli_repo` | Source of reusable workflows | No (default: ikaruce/ai-cli-workflow) |
| `api_key` | Static bearer token for `/api/v1/token` clients | Yes |
| `app_name` | Used in PR titles + template substitution | No (default: aibot) |

Loaded from `.env` file via `@lru_cache get_settings()`.

## Key Modules

| Module | Purpose | Key Functions |
|--------|---------|---|
| `github/auth.py` | JWT + token exchange | `generate_jwt()`, `get_installation_token(id)`, `get_repo_installation_id(repo)` |
| `github/workflow.py` | PR creation logic | `create_dispatch_pr(token, repo)`, `provision_repos(id, repos, token)` |
| `github/client.py` | Shared helpers | `_get_all_repos(token)` (paginated fetch) |
| `webhook/verify.py` | HMAC verification | `verify_signature(body, signature)` |
| `webhook/router.py` | Endpoints | `POST /webhook`, `GET /health` |
| `webhook/handlers/installation.py` | Event handlers | `handle_installation(payload)`, `handle_installation_repositories(payload)` |
| `api/token.py` | Token API | `POST /api/v1/token`, `_verify_api_key(auth)` |

## Data Flow: Installation Webhook → Dispatch PR

```
Webhook Request
    │
    ├─→ webhook/router.py::webhook()
    │   ├─→ verify_signature() [HMAC-SHA256]
    │   ├─→ await request.json()
    │   └─→ Match X-GitHub-Event header
    │
    ├─→ webhook/handlers/installation.py::handle_installation()
    │   ├─→ Extract installation_id, action, repository_selection
    │   ├─→ If action="created":
    │   │   ├─→ If repo_selection="all":
    │   │   │   ├─→ get_installation_token(id) → (token, expires_at)
    │   │   │   └─→ _get_all_repos(token) → [repos]
    │   │   └─→ Else: repos = payload["repositories"]
    │   └─→ provision_repos(installation_id, repos)
    │
    └─→ github/workflow.py::provision_repos()
        ├─→ For each repo:
        │   └─→ create_dispatch_pr(token, full_name)
        │       ├─→ GET /repos/{repo}/default_branch
        │       ├─→ GET /repos/{repo}/git/ref/heads/{default}
        │       ├─→ GET /repos/{repo}/contents/.github/workflows/ai-cli-dispatch.yml
        │       ├─→ Create or reset feature branch
        │       ├─→ PUT workflow file (template rendered)
        │       └─→ POST /pulls (create PR with templated body)
        └─→ Log: "PR created for {repo}"
```

## Templates

| File | Purpose | Substitutions |
|------|---------|---|
| `templates/dispatch.yml` | GitHub Actions workflow to dispatch | `{{APP_NAME}}`, `{{AICLI_REPO}}` |
| `templates/pr_body.md` | Markdown body for provisioning PR | `{{APP_NAME}}` + Korean "update" message |

## External Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| **fastapi** | Web framework | ≥0.136.1 |
| **uvicorn[standard]** | ASGI server | ≥0.46.0 |
| **httpx** | Async HTTP client | ≥0.28.1 |
| **pyjwt[crypto]** | RS256 JWT signing | ≥2.12.1 |
| **pydantic-settings** | Config management | ≥2.14.0 |
| pytest / pytest-asyncio / respx | Testing | Dev only |

## Deployment

**Docker Entry:** `Dockerfile` → `uvicorn aibot.main:app --host 0.0.0.0 --port 8000`

**Testing:** 5 test files (14 total test modules) covering auth, workflows, installation handlers, verification, and token API.
