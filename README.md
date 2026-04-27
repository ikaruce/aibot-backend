# aibot — AI CLI GitHub App Backend

GitHub App backend that provisions AI CLI dispatch workflows to user repositories via PR on installation.

---

## Architecture Overview

```
GitHub App installed on user repo
        │
        ▼ webhook (installation.created)
  POST /webhook  ──► provision_repos()
        │               │
        │               ▼ GitHub API
        │         create branch → commit workflow → open PR
        │
  User repo gains:  .github/workflows/ai-cli-dispatch.yml
        │
        ▼ (PR merged, secrets set)
  PR opened / @ai-cli comment
        │
        ▼ dispatch workflow
  ai-skill-runner.yml  (ikaruce/ai-cli-workflow)
        │
        ▼ needs a GitHub App token
  POST /api/v1/token  ──► fresh installation token (1 hr TTL)
```

---

## Setup Guide

### 1. Create a GitHub App

Go to **Settings → Developer settings → GitHub Apps → New GitHub App** (personal or org).

| Field | Value |
|-------|-------|
| GitHub App name | `aibot` (or your preferred name) |
| Homepage URL | your server URL |
| Webhook URL | `https://<your-server>/webhook` |
| Webhook secret | generate a random string (saved as `GITHUB_WEBHOOK_SECRET`) |

**Permissions (Repository):**

| Permission | Access |
|------------|--------|
| Contents | Read & write |
| Pull requests | Read & write |
| Issues | Read & write |
| Metadata | Read-only (required) |

**Subscribe to events:**
- `Installation` (account-level)

After creation:
1. Note the **App ID** → `GITHUB_APP_ID`
2. **Generate a private key** → download `.pem` file → `GITHUB_PRIVATE_KEY`
3. **Install the app** on your test repository

---

### 2. Configure the Backend

Copy the example env file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEow...
-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_random_secret
API_KEY=any_random_string_you_generate    # used by Actions to call /api/v1/token
APP_NAME=aibot
AICLI_REPO=ikaruce/ai-cli-workflow
```

> **Tip:** For multi-line private key in `.env`, wrap the entire value in double quotes, preserving newlines.

---

### 3. Run the Backend

**Docker Compose (recommended):**

```bash
docker compose up -d
```

**Local (with uv):**

```bash
uv sync
uv run uvicorn aibot.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

### 4. Expose Webhook URL (Local Testing)

For local testing, use [ngrok](https://ngrok.com) to expose the server:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL and update the **Webhook URL** in your GitHub App settings:

```
https://xxxx.ngrok-free.app/webhook
```

---

### 5. Test: App Installation Flow

Install the app on a test repository via **GitHub App settings → Install App**.

The backend will:
1. Receive the `installation.created` webhook
2. Create branch `add-ai-cli-dispatch-workflow` in your repo
3. Commit `.github/workflows/ai-cli-dispatch.yml`
4. Open a PR titled **"[aibot] AI CLI 디스패치 워크플로우 추가"**

Merge the PR to activate the dispatch workflow.

Check backend logs:

```bash
docker compose logs -f aibot
```

---

### 6. Set Repository Secrets and Variables

After merging the PR, configure the following on your test repository.

**Secrets** (**Settings → Secrets and variables → Actions → Secrets**):

| Secret | Value |
|--------|-------|
| `AI_CLI_API_KEY` | Your Gemini API key (or other AI provider key) |
| `AI_CLI_APP_TOKEN` | The `API_KEY` value from your backend's `.env` |

**Variables** (**Settings → Secrets and variables → Actions → Variables**):

| Variable | Value |
|----------|-------|
| `AIBOT_URL` | Your backend URL, e.g. `https://xxxx.ngrok-free.app` |

`AI_CLI_APP_TOKEN` is the **static API key for the aibot backend** — not a GitHub token. The dispatch workflow calls `/api/v1/token` at runtime to fetch a fresh GitHub installation token each time. The token never touches repository secrets.

---

### 7. Test: PR Review

Create a PR on your test repository. The dispatch workflow will:
1. Detect the `pull_request` event
2. Call `ikaruce/ai-cli-workflow/.github/workflows/ai-skill-runner.yml@main`
3. Run the `code-review-commons` skill against the PR diff
4. Post a review comment

---

### 8. Test: `@ai-cli` Command

On any PR, post a comment:

```
@ai-cli 이 PR의 보안 취약점을 분석해줘
```

or

```
@ai-cli summarize the changes in this PR
```

The dispatch workflow detects the `@ai-cli` mention and calls `ai-command.yml@main` with the free-form instruction.

---

### 9. Optional Repository Variables

These variables can be set per-repository (**Settings → Secrets and variables → Actions → Variables**) to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_CLI_SKILL` | `code-review-commons` | Skill to run on PR events |
| `AI_CLI_RULES` | `code-inspection-common` | Rules applied during skill execution |
| `AI_CLI_APP_NAME` | `aibot` | Display name in posted comments |

---

## API Reference

### `GET /health`

```bash
curl https://<server>/health
# {"status":"ok"}
```

### `POST /api/v1/token`

Issues a fresh GitHub App installation token for the specified repository.

```bash
curl -X POST https://<server>/api/v1/token \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo"}'
```

Returns `404` if the app is not installed on the repository.

---

## Development

```bash
uv sync
uv run pytest tests/ -v   # 27 tests
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_APP_ID` | ✓ | — | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | ✓ | — | RSA private key (PEM) |
| `GITHUB_WEBHOOK_SECRET` | ✓ | — | HMAC secret for webhook verification |
| `API_KEY` | ✓ | — | Bearer token for `/api/v1/token` |
| `APP_NAME` | — | `aibot` | Display name in PRs and comments |
| `AICLI_REPO` | — | `ikaruce/ai-cli-workflow` | Source repo for reusable workflows |
| `GITHUB_BASE_URL` | — | `https://github.com` | Override for GitHub Enterprise |
