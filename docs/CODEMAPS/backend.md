<!-- Generated: 2026-04-27 | Files scanned: 10 | Token estimate: ~850 -->

# Backend API Codemap

**Last Updated:** 2026-04-27  
**Routes Count:** 3 (1 webhook, 1 health check, 1 token API)  
**Entry Point:** `src/aibot/main.py::create_app()`

## API Endpoints

### Health Check

```
GET /health
├─ Response: {"status": "ok"}
└─ No auth required
```

**File:** `src/aibot/webhook/router.py::health()`

---

### Webhook Receiver

```
POST /webhook
├─ Headers (Required):
│  ├─ X-Hub-Signature-256: "sha256=<hex>"  (HMAC-SHA256)
│  └─ X-GitHub-Event: "installation" | "installation_repositories" | ...
├─ Body: JSON webhook payload
├─ Response: {"status": "ok"}
└─ Status: 401 if signature missing/invalid, 200 on success
```

**File:** `src/aibot/webhook/router.py::webhook(request, x_hub_signature_256, x_github_event)`

**Signature Verification:**
```python
# src/aibot/webhook/verify.py::verify_signature(body: bytes, signature: str | None)
expected = "sha256=" + hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()
if not hmac.compare_digest(expected, signature):
    raise HTTPException(status_code=401, detail="Invalid webhook signature")
```

**Event Handlers:**

| Event | Handler | Action |
|-------|---------|--------|
| `installation` | `handle_installation(payload)` | New app install → provision repos |
| `installation_repositories` | `handle_installation_repositories(payload)` | Repos added → provision |
| *(other)* | Logged as debug, no action | Silently ignored |

---

### Token Issue API

```
POST /api/v1/token
├─ Auth: Header Authorization = "Bearer {api_key}"
├─ Request Body: {"repo": "owner/name"}
├─ Response: {"token": "ghu_*", "expires_at": "2026-04-28T...Z"}
└─ Status: 200 on success, 401 if auth fails, 404 if app not installed
```

**File:** `src/aibot/api/token.py`

**Request Validation:**
```python
class TokenRequest(BaseModel):
    repo: str
    
    @field_validator("repo")
    def repo_must_be_owner_slash_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", v):
            raise ValueError("repo must be in 'owner/name' format")
        return v
```

**Response Model:**
```python
class TokenResponse(BaseModel):
    token: str          # GitHub installation access token
    expires_at: str     # ISO-8601 timestamp
```

**Authentication:**
```python
def _verify_api_key(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    key = authorization.removeprefix("Bearer ").strip()
    if key != get_settings().api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Flow:**
1. Verify Bearer token against `Settings.api_key`
2. Call `get_repo_installation_id(repo)` to find GitHub App installation ID
   - Uses JWT auth, no prior state needed
   - Returns 404 if app not installed on repo
3. Call `get_installation_token(installation_id)` to mint fresh token
4. Return token + expiry timestamp to caller

---

## Router Registration

**File:** `src/aibot/main.py`

```python
def create_app() -> FastAPI:
    app = FastAPI(title="aibot — AI CLI GitHub App")
    app.include_router(webhook_router)      # from aibot.webhook.router
    app.include_router(token_router)        # from aibot.api.token (prefix="/api/v1")
    return app

app = create_app()
```

## GitHub API Calls

All async HTTP calls via `httpx.AsyncClient()` with Bearer token or JWT auth.

| Operation | Endpoint | Auth | File |
|-----------|----------|------|------|
| **Generate JWT** | N/A (local) | Private key | `github/auth.py::generate_jwt()` |
| **Get install token** | `POST /app/installations/{id}/access_tokens` | JWT | `github/auth.py::get_installation_token(id)` |
| **Lookup install ID** | `GET /repos/{repo}/installation` | JWT | `github/auth.py::get_repo_installation_id(repo)` |
| **List repos** | `GET /installation/repositories` (paginated) | Installation token | `github/client.py::_get_all_repos(token)` |
| **Get repo details** | `GET /repos/{repo}` | Installation token | `github/workflow.py::create_dispatch_pr()` |
| **Get branch ref** | `GET /repos/{repo}/git/ref/heads/{branch}` | Installation token | `github/workflow.py::create_dispatch_pr()` |
| **Get file contents** | `GET /repos/{repo}/contents/{path}` | Installation token | `github/workflow.py::create_dispatch_pr()` |
| **Create/reset branch** | `POST /repos/{repo}/git/refs` + `PATCH /repos/{repo}/git/refs/heads/{branch}` | Installation token | `github/workflow.py::create_dispatch_pr()` |
| **Commit file** | `PUT /repos/{repo}/contents/{path}` | Installation token | `github/workflow.py::create_dispatch_pr()` |
| **Create PR** | `POST /repos/{repo}/pulls` | Installation token | `github/workflow.py::create_dispatch_pr()` |

## Request/Response Examples

### Token API Success
```bash
curl -X POST http://localhost:8000/api/v1/token \
  -H "Authorization: Bearer secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"repo": "myorg/myrepo"}'

# Response 200:
{
  "token": "ghu_16C7e42F292c6912E7710c838347Ae178B4a",
  "expires_at": "2026-04-28T14:57:00Z"
}
```

### Token API 404 (Not Installed)
```
Response 404:
{
  "detail": "App is not installed on repository: badorg/badrepo"
}
```

### Webhook Example
```bash
curl -X POST http://localhost:8000/webhook \
  -H "X-Hub-Signature-256: sha256=abcd1234..." \
  -H "X-GitHub-Event: installation" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "created",
    "installation": {"id": 12345, "repository_selection": "selected"},
    "repositories": [{"full_name": "owner/repo1"}, {"full_name": "owner/repo2"}]
  }'

# Response 200:
{"status": "ok"}
```

## Logging

All modules use `logging.getLogger(__name__)`. Key log points:

- `github/auth.py` — Silent (production mode)
- `github/client.py` — `logger.error()` on fetch failures
- `github/workflow.py` — `logger.info()` on PR creation, `logger.error()` on provision failures
- `webhook/handlers/installation.py` — `logger.info()` on events
- `api/token.py` — `logger.info()` on token issuance

**Configure via environment or `logging.basicConfig()` in `main.py` (currently INFO level).**
