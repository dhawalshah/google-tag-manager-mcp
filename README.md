# Google Tag Manager MCP

A Python Model Context Protocol (MCP) server for the Google Tag Manager API v2. Connect Claude (or any MCP-compatible AI client) directly to your GTM accounts to manage tags, triggers, variables, workspaces, versions, environments, and more — all in natural language.

The server is also an OAuth 2.1 authorization server, so it works as a remote connector anywhere Claude supports custom MCP servers — claude.ai (personal), Claude Desktop, and Claude Teams. For Teams, the org owner adds the URL once and each member authenticates individually on first use.

## Tools (18 consolidated per-resource tools)

Each tool takes an `action` parameter that selects the operation, plus resource addressing (`parent` / `path`) and optional `config`, `params`, and `confirm` fields. Destructive actions require `confirm=True`.

| Tool | Actions |
| --- | --- |
| `gtm_account` | get, list, update |
| `gtm_container` | create, get, list, update, remove + combine, lookup, move_tag_id, snippet |
| `gtm_workspace` | create, get, list, update, remove + create_version, get_status, sync, quick_preview, resolve_conflict |
| `gtm_tag` | create, get, list, update, remove, revert |
| `gtm_trigger` | create, get, list, update, remove, revert |
| `gtm_variable` | create, get, list, update, remove, revert |
| `gtm_built_in_variable` | create, list, remove, revert |
| `gtm_folder` | create, get, list, update, remove + revert, entities, move_entities_to_folder |
| `gtm_client` | create, get, list, update, remove, revert |
| `gtm_zone` | create, get, list, update, remove, revert |
| `gtm_template` | create, get, list, update, remove + revert, import_from_gallery |
| `gtm_transformation` | create, get, list, update, remove, revert |
| `gtm_gtag_config` | create, get, list, update, remove |
| `gtm_destination` | get, list, link |
| `gtm_environment` | create, get, list, update, remove + reauthorize |
| `gtm_version` | get, live, publish, set_latest, undelete, update, remove |
| `gtm_version_header` | list, latest |
| `gtm_user_permission` | create, get, list, update, remove |

### Consolidated tool design

Each tool takes a uniform set of parameters:

- `action` — the operation to perform (e.g. `"list"`, `"create"`, `"publish"`)
- `parent` — resource path of the parent (e.g. `"accounts/123/containers/456/workspaces/7"`) — used for create and list
- `path` — full resource path of the entity — used for get, update, remove, and other single-resource operations
- `config` — dict of fields for create / update body
- `params` — dict of extra query parameters
- `confirm` — boolean, required `True` for destructive actions

Example — list tags in a workspace:

```python
gtm_tag(action="list", parent="accounts/123/containers/456/workspaces/7")
```

Example — publish a version (destructive, requires confirmation):

```python
gtm_version(action="publish", path="accounts/123/containers/456/versions/9", confirm=True)
```

### Confirmation guardrail

The following actions are considered destructive and require `confirm=True`. Without it, the tool immediately returns a structured message asking you to re-call with `confirm=True`:

> publish, remove, revert, undelete, combine, move_tag_id, move_entities_to_folder, sync, create_version, resolve_conflict, reauthorize, link

This prevents accidental mutations from ambiguous prompts.

---

## How auth works

There are **two** modes. Pick one.

### Mode A — Local STDIO (one user, no server)

Use this if you only want it on your own machine. `setup_local_auth.py` runs the Google OAuth flow once and stores your token in `~/.config/gtm-mcp/token.json`. Claude Desktop launches `server.py` as a subprocess. No Firestore, no Cloud Run, no public URL.

### Mode B — Remote HTTP server (Claude Teams, claude.ai, multi-user)

The MCP server is also an OAuth 2.1 authorization server. When Claude connects:

1. Claude discovers our metadata at `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.
2. Claude registers itself via Dynamic Client Registration (`POST /oauth/register`).
3. Claude redirects the user to `/oauth/authorize`. We delegate identification to Google OAuth.
4. After Google login, we issue our **own** opaque bearer token to Claude — Google credentials never leave the server.
5. On each `/mcp` request Claude sends our bearer; we map it server-side to the right user's stored Google credentials and call the GTM APIs.

---

## Prerequisites

- Python 3.10+
- A Google Tag Manager account you have access to
- A [Google Cloud](https://console.cloud.google.com/) project

---

## Step 1 — Set up Google Cloud

### 1a. Create a project and enable the Tag Manager API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. **APIs & Services → Library**, enable **Tag Manager API**.

### 1b. Create OAuth 2.0 credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
2. Application type: **Web application**.
3. Add **Authorized redirect URIs**:
   - `http://localhost:8080/auth/callback` *(local dev / setup_local_auth.py)*
   - `https://YOUR-CLOUD-RUN-URL/auth/callback` *(remote deployment — add after deploy)*
4. Click **Create**, then **Download JSON** → save as `client_secret.json` in the project root *(gitignored)*. You can also copy the Client ID / Client Secret straight into env vars.

### 1c. OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. Choose **Internal** for a Google Workspace org (recommended for teams), or **External** for personal/individual use.
3. Add scopes:
   - `https://www.googleapis.com/auth/tagmanager.readonly`
   - `https://www.googleapis.com/auth/tagmanager.edit.containers`
   - `https://www.googleapis.com/auth/tagmanager.delete.containers`
   - `https://www.googleapis.com/auth/tagmanager.edit.containerversions`
   - `https://www.googleapis.com/auth/tagmanager.publish`
   - `https://www.googleapis.com/auth/tagmanager.manage.users`
4. If using **External** in Testing mode, add each user's email under **Test users**.

### 1d. Enable Firestore *(Mode B only)*

The server stores OAuth bearer tokens and per-user Google credentials in Firestore (collection `user_tokens_gtm`).

1. In Cloud Console, **Firestore → Create database → Native mode**, pick a region.
2. Grant the Cloud Run service account **Cloud Datastore User** role under **IAM & Admin → IAM**.

---

## Step 2 — Install

```bash
git clone https://github.com/dhawalshah/gtm-mcp
cd gtm-mcp
pip install -r requirements.txt
cp .env.example .env       # fill in values
```

---

## Step 3 — Mode A: Local STDIO

```bash
python setup_local_auth.py
```

A browser opens, you sign in with Google, the script writes `~/.config/gtm-mcp/token.json`.

Then add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "google-tag-manager": {
      "command": "python",
      "args": ["/absolute/path/to/gtm-mcp/server.py"],
      "env": {
        "OAUTH_CONFIG_PATH": "/absolute/path/to/client_secret.json",
        "MCP_USER_EMAIL": "you@yourcompany.com"
      }
    }
  }
}
```

Restart Claude Desktop. You're done — skip the rest.

---

## Step 3 — Mode B: Remote HTTP server (Claude Teams / claude.ai)

### Deploy to Cloud Run

```bash
gcloud run deploy gtm-mcp \
  --source . \
  --region YOUR_REGION \
  --project YOUR_PROJECT_ID \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=your-project-id,BASE_URL=https://YOUR-SERVICE-URL.run.app,OAUTHLIB_RELAX_TOKEN_SCOPE=1,ALLOWED_DOMAINS=yourcompany.com" \
  --set-secrets "OAUTH_CONFIG_PATH=gtm-mcp-client-secret:latest"
```

**Required:** `OAUTHLIB_RELAX_TOKEN_SCOPE=1` — Google's OAuth response often returns a superset of the requested scopes; without this env var, `google-auth-oauthlib` raises "Scope has changed" in `/auth/callback` and the entire auth flow fails.

**Recommended:** load `client_secret.json` from [Secret Manager](https://cloud.google.com/secret-manager) rather than baking it into the image or passing the raw secret as a plain env var. Store the file as a secret, then mount it at runtime via `--set-secrets`.

After it's up, go back to **APIs & Services → Credentials → your OAuth client** and add the live callback URL:

```
https://YOUR-SERVICE-URL.run.app/auth/callback
```

### Connect from Claude

**Claude Teams (org owner adds it once for everyone):**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`
- Each member clicks **Connect**, signs in with Google, done.

**claude.ai personal:**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`

**Claude Desktop with a remote server:**
```json
{
  "mcpServers": {
    "google-tag-manager": {
      "url": "https://YOUR-SERVICE-URL.run.app/mcp"
    }
  }
}
```

---

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `BASE_URL` | Mode B | Public URL of this service. Used for OAuth metadata and as the canonical resource URI tokens are bound to. |
| `GCP_PROJECT_ID` | Mode B | GCP project hosting Firestore. |
| `OAUTH_CONFIG_PATH` | Both† | Path to `client_secret.json` downloaded from Google Cloud Console. |
| `GOOGLE_CLIENT_ID` | Mode B† | Google OAuth client ID (alternative to `OAUTH_CONFIG_PATH`). |
| `GOOGLE_CLIENT_SECRET` | Mode B† | Google OAuth client secret (alternative to `OAUTH_CONFIG_PATH`). |
| `OAUTHLIB_RELAX_TOKEN_SCOPE` | Mode B | Set to `1`. Required — Google returns a superset scope and without this the OAuth callback fails. |
| `MCP_USER_EMAIL` | Mode A | Your email — set in Claude Desktop config so the server finds your stored token. |
| `ALLOWED_DOMAINS` | No | Comma-separated email domain allowlist (e.g. `acme.com,beta.com`). Empty = no restriction. |
| `PORT` | No | HTTP port (default `8080`). |
| `LOG_LEVEL` | No | Python log level (default `INFO`). |

† Set **either** `OAUTH_CONFIG_PATH` **or** `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET`.

---

## Quota

The GTM API v2 has a low default quota: approximately **0.25 QPS**, **15 requests/minute**, and **10,000 requests/day** per GCP project. Unlike Google Ads or Analytics, the quota does not auto-upgrade with billing.

If you hit quota errors, raise limits via **Cloud Console → APIs & Services → Tag Manager API → Quotas & System Limits**.

The client has built-in rate throttling and exponential backoff to stay within default limits during normal use.

---

## OAuth endpoint reference (Mode B)

| Endpoint | Spec | Purpose |
| --- | --- | --- |
| `GET /.well-known/oauth-protected-resource` | RFC 9728 | Advertises the canonical resource URI and authorization server. |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 | Authorization server metadata. |
| `POST /oauth/register` | RFC 7591 | Dynamic Client Registration. |
| `GET /oauth/authorize` | OAuth 2.1 | Starts the auth code flow with PKCE; redirects to Google. |
| `GET /auth/callback` | — | Google redirects here; we mint our authorization code and bounce back to the MCP client. |
| `POST /oauth/token` | OAuth 2.1 | Authorization code + refresh token grants. |

A `GET /mcp` without a valid bearer returns `401` with a `WWW-Authenticate: Bearer resource_metadata="…"` header pointing at the protected-resource metadata document, which is how a standards-compliant MCP client discovers the rest.

---

## Reference

The `reference/` folder holds the upstream [stape-io/gtm-mcp](https://github.com/stape-io/gtm-mcp) TypeScript server, cloned as an API-shape reference during development. It is listed in `.gitignore` and excluded from Docker/Cloud Run builds — it is not part of the deployable app.

---

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **FastAPI + uvicorn** — HTTP wrapper
- **Google Auth / google-api-python-client** — Google OAuth and API access
- **Firestore** — Per-user token storage and OAuth-server state (Mode B)
- **Google Cloud Run** — Serverless hosting

---

## About Dhawal Shah

<img src="https://www.dhawalshah.net/images/illustrations/about-dhawal-shah.webp" alt="Caricature of Dhawal Shah" align="right" width="155">

I run a 40-plus person digital marketing agency out of Singapore, and I build the
automation my own teams use. This server is one of those tools rather than a weekend
project: it runs against live Tag Manager accounts every week, which is why the
read-only surface is wide and the write surface is deliberately narrow.

Fourteen years building companies across Asia behind it. 5,000+ campaigns, 400+ brands,
30+ startups advised, and 300+ training sessions for teams including Sony, Toyota, DHL
and Interpol. I am also an Accredited Director with the Singapore Institute of Directors,
which in practice means I get asked what breaks, who is accountable and what it costs
before anyone asks what it can do.

I write up the routines and agents I actually run at [dhawalshah.net](https://www.dhawalshah.net/about/?utm_source=github.com&utm_medium=referral&utm_campaign=google-tag-manager-mcp&utm_content=readme).

Worth reading alongside this repo: [Claude Code for Marketing: Every Channel from One Terminal](https://www.dhawalshah.net/article/claude-code-for-marketing/?utm_source=github.com&utm_medium=referral&utm_campaign=google-tag-manager-mcp&utm_content=readme).

---

## License

MIT
