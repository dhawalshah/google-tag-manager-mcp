# Google Tag Manager MCP — Design Spec

**Date:** 2026-06-05
**Author:** Dhawal Shah
**Status:** Approved design, pre-implementation

## 1. Purpose

A Model Context Protocol server for the Google Tag Manager API v2, built for the
team. It joins the existing `team-mcp` fleet of Google connectors (Analytics,
Search Console, Ads) and must follow the same structure, auth model, and
deployment pattern so it is operationally identical to its siblings.

It exposes GTM as MCP tools so the team can read, edit, and publish Tag Manager
configuration (containers, workspaces, tags, triggers, variables, versions, etc.)
through any MCP client (Claude Desktop, etc.), either locally or as a shared
Cloud Run service.

## 2. Background & key decisions

The starting reference is the open-source `stape-io/google-tag-manager-mcp-server`.
Research established:

- **The stape repo** is TypeScript on Cloudflare Workers, HTTP/SSE transport, with
  OAuth baked in as a self-hosted provider. It exposes **19 consolidated tools**
  (one per GTM resource, each with an `action` parameter) and has near-complete
  GTM API v2 coverage (only notable gap: `workspaces.bulk_update`).
- **The team's connectors** are a different stack entirely: Python + FastAPI +
  FastMCP on Cloud Run, with the team's own OAuth 2.1 protected-resource server,
  Firestore token storage, and a `current_user_email` ContextVar.

Because the stack, framework, transport, auth model, and tool philosophy all
differ, the stape repo cannot be "cloned and edited" into the team pattern — that
would be a rewrite. It is therefore used as a **reference spec** for *which* GTM
operations to wrap and how to shape their inputs, while the actual build is a
**fresh Python connector** that mirrors the `google-search-console-mcp` (GSC)
connector.

### Decisions made during brainstorming

| Decision | Choice |
|---|---|
| Build approach | Fresh Python scaffold mirroring GSC; stape repo kept in `reference/` for lookup |
| Tool design | Consolidated per-resource (18 `gtm_<resource>` tools, each with an `action` param) |
| Capability scope | Full read + edit + publish (all six GTM scopes) |
| Safety guardrail | Confirmation token (`confirm=true`) required for destructive actions |
| Deployment | Dual-mode: local STDIO **and** remote Cloud Run (inherited from GSC pattern) |

## 3. Why consolidated tools (not flat)

The team's existing connectors use flat, one-tool-per-operation registration
(`list_properties`, `get_search_analytics`, …), which works because each service
has ~15–25 operations. GTM has ~19 resource types × ~6 actions = **100+
operations**. Registering those flat would flood the model's tool list, burn
context, and degrade tool-selection accuracy.

Consolidated design collapses this to **18 tools**, one per resource, with an
`action` parameter selecting the operation:

```
gtm_tag(action="list",   workspace_path=...)
gtm_tag(action="create", workspace_path=..., config={...})
gtm_tag(action="remove", tag_path=..., confirm=true)
```

GTM is the fleet's exception on this point, justified by its size.

## 4. Architecture & file layout

A fresh Python connector mirroring `google-search-console-mcp`. Same stack:
FastAPI + FastMCP on Cloud Run, OAuth 2.1 protected-resource server, Firestore
token storage, `current_user_email` ContextVar, STDIO local mode.

```
gtm-mcp/
├── main.py                  # FastAPI app: mounts /mcp, oauth router, bearer auth middleware
│                            #   (copied from GSC, renamed strings)
├── server.py                # FastMCP registration — imports the 18 gtm_<resource> tools
├── gtm/
│   ├── __init__.py
│   ├── client.py            # shared: auth headers, request helpers, THROTTLE + backoff,
│   │                        #   audit log, format_response/format_error, confirm-guard helper
│   ├── accounts.py          # gtm_account         (get, list, update)
│   ├── containers.py        # gtm_container       (create, get, list, update, remove,
│   │                        #                       combine, lookup, move_tag_id, snippet)
│   ├── workspaces.py        # gtm_workspace       (create, get, list, update, remove,
│   │                        #                       create_version, get_status, sync,
│   │                        #                       quick_preview, resolve_conflict)
│   ├── tags.py              # gtm_tag             (create, get, list, update, remove, revert)
│   ├── triggers.py          # gtm_trigger         (create, get, list, update, remove, revert)
│   ├── variables.py         # gtm_variable        (create, get, list, update, remove, revert)
│   ├── builtin_variables.py # gtm_built_in_variable (create, list, remove, revert)
│   ├── folders.py           # gtm_folder          (create, get, list, update, remove, revert,
│   │                        #                       entities, move_entities)
│   ├── clients.py           # gtm_client          (create, get, list, update, remove, revert)
│   ├── zones.py             # gtm_zone            (create, get, list, update, remove, revert)
│   ├── templates.py         # gtm_template        (create, get, list, update, remove, revert,
│   │                        #                       import_from_gallery)
│   ├── transformations.py   # gtm_transformation  (create, get, list, update, remove, revert)
│   ├── gtag_config.py       # gtm_gtag_config     (create, get, list, update, remove)
│   ├── destinations.py      # gtm_destination     (get, list, link, unlink)
│   ├── environments.py      # gtm_environment     (create, get, list, update, remove, reauthorize)
│   ├── versions.py          # gtm_version         (get, live, publish, set_latest, undelete,
│   │                        #                       update, remove)
│   ├── version_headers.py   # gtm_version_header  (list, latest)
│   └── user_permissions.py  # gtm_user_permission (create, get, list, update, remove)
├── oauth/                   # copied from GSC verbatim, with targeted changes:
│   ├── __init__.py
│   ├── oauth_server.py      #   (unchanged)
│   ├── token_store.py       #   (unchanged — shared oauth_* collections)
│   ├── google_auth.py       #   SCOPES → the 6 GTM scopes; local token path renamed
│   └── firestore_tokens.py  #   COLLECTION = "user_tokens_gtm"
├── reference/               # stape-io TS repo, cloned read-only as an operation/shape reference
├── tests/                   # mirror GSC tests/: per-resource unit tests w/ mocked GTM responses
├── Dockerfile
├── requirements.txt
├── setup_local_auth.py      # STDIO local mode (renamed paths + GTM scopes)
├── manifest.json            # DXT manifest (renamed, GTM tool list, dual-mode notes)
├── client_secret.json.example
├── .env.example
├── .gitignore / .dockerignore / .gcloudignore
└── README.md
```

One tool = one resource module, matching the consolidated decision and stape's
`tools/` layout.

## 5. Tool surface & guardrail

- **18 consolidated tools**, each `gtm_<resource>(action=..., <args>)`. The
  `action` is validated against an allowed set per resource; an unknown action
  returns a `format_error` that lists the valid actions for that resource.
- **Confirmation token.** Any action in the destructive set requires `confirm=true`
  in the call. Without it the tool returns a structured message
  (`"This will <effect>; re-call with confirm=true to proceed"`) instead of
  executing. Read/create/update proceed normally.

  Destructive set (require `confirm=true`):
  `publish`, `remove`, `revert`, `undelete`, `combine`, `resolve_conflict`,
  `move_tag_id`.

- **Response envelope.** Reuse GSC's `format_response` / `format_error`
  `{success, data, metadata, error}` shape verbatim, keeping the fleet consistent.

## 6. Auth, quota & deployment

### Auth
Identical OAuth 2.1 flow to GSC (DCR + PKCE, server proxies user auth to Google,
issues opaque bearers validated in middleware which sets `current_user_email`).

Six GTM scopes:
- `https://www.googleapis.com/auth/tagmanager.readonly`
- `https://www.googleapis.com/auth/tagmanager.edit.containers`
- `https://www.googleapis.com/auth/tagmanager.delete.containers`
- `https://www.googleapis.com/auth/tagmanager.edit.containerversions`
- `https://www.googleapis.com/auth/tagmanager.publish`
- `https://www.googleapis.com/auth/tagmanager.manage.users`

`OAUTHLIB_RELAX_TOKEN_SCOPE=1` must be set on every deploy (Google returns a
superset scope; without this the callback fails). `client_secret.json` is loaded
from Secret Manager — never baked into the image.

### Firestore
Shared GCP project. Own per-MCP token collection `user_tokens_gtm`. Shared
`oauth_*` collections for the embedded auth server (clients, pending, codes,
tokens, refresh).

### Quota handling (the one genuinely new piece of logic)
GTM's default quota is low: ~**0.25 QPS** (~15 req/min) and **10,000 req/day** per
project. It does **not** auto-upgrade; it can be raised manually via Cloud Console
→ APIs & Services → Tag Manager API → Quotas (with justification, subject to
review). For interactive team use this is not expected to be a constraint.

`gtm/client.py` therefore adds a client-side **throttle + exponential backoff**
with retry on HTTP 429 and 403-rate-limit responses — more than GSC's fixed
per-user counter. A brief burst (e.g. listing tags across many containers) waits
and retries transparently instead of erroring.

### Deployment — dual mode (inherited, not either/or)
| | Local (STDIO) | Remote (Cloud Run) |
|---|---|---|
| Audience | single user (you) | the team |
| Setup | `python setup_local_auth.py` once → browser consent → token at `~/.config/gtm-mcp/token.json` | `deploy.sh` once |
| Auth | `MCP_USER_EMAIL` env + local token file | full OAuth 2.1; each teammate signs in via their client |
| Run | Claude Desktop spawns `server.py` (DXT/manifest.json) | hosted `/mcp` HTTPS, bearer-auth |
| Firestore | not required (local file) | `user_tokens_gtm` |

`oauth/google_auth.py` selects the path automatically: a bearer-derived
`current_user_email` (remote) else `MCP_USER_EMAIL` + local token (local). The
connector can be used **entirely locally** without ever deploying to Cloud Run;
Cloud Run is purely additive for team sharing. Add a `gtm` entry to the existing
`deploy.sh` pattern when remote deploy is wanted.

## 7. Build sequence

1. Clone stape into `reference/`; scaffold dirs; copy `oauth/`, `main.py`, and a
   `client.py` skeleton from GSC; adjust names, scopes, and the Firestore
   collection.
2. Build `gtm/client.py` first (throttle/backoff/confirm-guard) — everything
   depends on it.
3. Implement resource modules in dependency order:
   accounts → containers → workspaces → entities (tags / triggers / variables /
   builtin_variables / folders / clients / zones / templates / transformations /
   gtag_config) → versions / version_headers → environments / destinations →
   user_permissions.
4. Register all tools in `server.py`.
5. Supporting files: `Dockerfile`, `requirements.txt`, `manifest.json`,
   `setup_local_auth.py`, `*.example`, ignore files, `README.md`.

## 8. Testing

Mirror GSC's `tests/`:
- Unit tests per resource module with **mocked GTM API responses** (no live API
  calls in CI).
- Action-routing tests: each resource rejects unknown actions with the valid-action
  list.
- Confirmation-guard tests: destructive actions refuse without `confirm=true` and
  proceed with it.
- Auth/middleware test: `/mcp` returns 401 + `WWW-Authenticate` without a valid
  bearer.

## 9. Out of scope for v1

- `workspaces.bulk_update` (the one GTM API gap in stape) — not included; entity
  edits are individual.
- Server-side / live preview tooling beyond `workspace.quick_preview`.
- Automated quota-increase request (manual Cloud Console action if ever needed).

## 10. Open questions

None outstanding. Design approved 2026-06-05.
