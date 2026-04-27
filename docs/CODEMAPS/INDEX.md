<!-- Generated: 2026-04-27 | Total Files: 14 Python modules | Token estimate: ~200 -->

# aibot-backend Codemaps Index

**Last Updated:** 2026-04-27  
**Project:** GitHub App backend provisioning AI CLI dispatch workflows  
**Stack:** Python 3.11, FastAPI, httpx, pyjwt

## Overview

aibot is a FastAPI GitHub App backend that automatically provisions AI CLI dispatch workflows to user repositories via pull requests. It exposes a webhook for GitHub App events and a REST API for on-demand GitHub installation token issuance.

## Codemaps

| Document | Purpose | Key Topics |
|----------|---------|-----------|
| **[architecture.md](./architecture.md)** | System design and GitHub App lifecycle | App lifecycle, auth layers, data flow, modules, templates, deployment |
| **[backend.md](./backend.md)** | API routes and request handling | Endpoints, signature verification, GitHub API calls, examples |
| **[dependencies.md](./dependencies.md)** | External services and packages | GitHub integration, production/dev deps, environment config, security |

## Quick Start

### Environment Setup
```bash
# Copy example and fill in GitHub App credentials
cp .env.example .env

# Install dependencies
uv sync

# Run tests
pytest

# Start dev server
uvicorn aibot.main:app --reload
```

### Key Endpoints

| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/health` | GET | Health check | None |
| `/webhook` | POST | GitHub App events | HMAC-SHA256 |
| `/api/v1/token` | POST | Issue GitHub token | Bearer API key |

### Environment Variables

Required in `.env`:
- `GITHUB_APP_ID` — GitHub App ID
- `GITHUB_PRIVATE_KEY` — RS256 private key (PEM format)
- `GITHUB_WEBHOOK_SECRET` — HMAC secret from App settings
- `API_KEY` — Static bearer token for `/api/v1/token`

Optional:
- `GITHUB_BASE_URL` — GitHub domain (default: https://github.com)
- `AICLI_REPO` — Source of workflows (default: ikaruce/ai-cli-workflow)
- `APP_NAME` — App name for titles (default: aibot)

## File Structure

```
src/aibot/
├── __init__.py
├── main.py                           # FastAPI app factory
├── config.py                         # Pydantic Settings
├── github/
│   ├── auth.py                       # JWT + token exchange
│   ├── client.py                     # GitHub API helpers
│   └── workflow.py                   # PR creation logic
├── webhook/
│   ├── router.py                     # /webhook, /health routes
│   ├── verify.py                     # HMAC signature verification
│   └── handlers/
│       └── installation.py           # Event handlers
└── api/
    └── token.py                      # POST /api/v1/token

templates/
├── dispatch.yml                      # GitHub Actions workflow template
└── pr_body.md                        # PR body template

tests/
├── conftest.py
├── github/
│   ├── test_auth.py
│   └── test_workflow.py
├── webhook/
│   ├── test_verify.py
│   └── test_installation.py
└── api/
    └── test_token.py
```

## Test Coverage

5 test modules (14 test files total):
- `tests/github/test_auth.py` — JWT generation, token exchange, installation ID lookup
- `tests/github/test_workflow.py` — PR creation and repo provisioning
- `tests/webhook/test_verify.py` — HMAC-SHA256 signature verification
- `tests/webhook/test_installation.py` — Installation and repo event handlers
- `tests/api/test_token.py` — Token API auth and issuance

**Run tests:** `pytest` or `pytest -v`

## Key Concepts

### GitHub App Lifecycle
1. User installs app on GitHub
2. GitHub sends `installation` or `installation_repositories` webhook
3. Backend verifies signature → routes to handler
4. Handler provisions dispatch workflow PR to each repo
5. GitHub Actions runs workflow → calls `/api/v1/token` for fresh token

### Authentication Flow
- **App → GitHub:** RS256 JWT (10 min TTL)
- **JWT → Installation Token:** OAuth exchange (1 hour TTL)
- **GitHub Actions → Backend:** Static API key via Bearer token

### Stateless Design
- No database or sessions
- All state in GitHub (repos, PRs, installation records)
- Credentials in environment variables only

## Related Resources

- [GitHub App API](https://docs.github.com/en/apps)
- [GitHub REST API v3](https://docs.github.com/en/rest)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx (async HTTP client)](https://www.python-httpx.org/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 on webhook | Invalid signature | Check `GITHUB_WEBHOOK_SECRET` matches App settings |
| 404 on `/api/v1/token` | App not installed | Install app on repo first |
| 401 on `/api/v1/token` | Invalid API key | Check `API_KEY` in request header |
| JWT errors | Private key format | Ensure key is PEM format with newlines escaped |
| PR not created | Missing write permissions | Check App permissions: Contents (read/write), Pull requests (read/write) |

## Performance & Monitoring

- **Concurrency:** Async FastAPI handles multiple requests
- **HTTP Client:** per-request `httpx.AsyncClient()` (production-grade pooling)
- **Logging:** INFO level by default; set `LOGLEVEL` env var to change
- **Timeouts:** httpx defaults (5s connect, 5s read); consider tuning for large repos
- **Docker:** Python 3.11-slim base, ~300MB image size

## Contact & Contributions

This backend integrates with the [AI CLI workflow](https://github.com/ikaruce/ai-cli-workflow) project. For issues or feature requests, see the main repository.
