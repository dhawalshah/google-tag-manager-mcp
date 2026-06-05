"""
OAuth 2.1 authorization server endpoints for the Google Tag Manager MCP.

Implements the subset required by the MCP authorization spec
(2025-06-18): RFC 9728 (Protected Resource Metadata), RFC 8414
(Authorization Server Metadata), RFC 7591 (Dynamic Client Registration),
RFC 8707 (Resource Indicators), and OAuth 2.1 PKCE.

The MCP server proxies OAuth: Claude (the MCP client) talks OAuth to us;
we delegate the actual user identification to Google. Google credentials
never leave the server — Claude only sees opaque tokens we issue.
"""

import os
import json
import base64
import hashlib
import hmac
import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import requests as http_requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow

from .firestore_tokens import save_token
from . import token_store
from .google_auth import SCOPES as _GTM_SCOPES

logger = logging.getLogger(__name__)

router = APIRouter()

# Google scopes: GTM scopes from google_auth plus identity scopes required for userinfo.
GOOGLE_SCOPES = _GTM_SCOPES + [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Scopes we advertise to MCP clients. Opaque to Google — we use this only
# for protocol completeness. We accept any requested scope.
ADVERTISED_SCOPES = ["tagmanager.readonly"]


def _base_url() -> str:
    return os.environ["BASE_URL"].rstrip("/")


def _canonical_resource() -> str:
    """The MCP resource URI clients must bind tokens to (RFC 8707)."""
    return f"{_base_url()}/mcp"


def _google_redirect_uri() -> str:
    return os.environ.get("GOOGLE_REDIRECT_URI") or f"{_base_url()}/auth/callback"


def _allowed_domains() -> list[str]:
    raw = os.environ.get("ALLOWED_DOMAINS", "").strip()
    if not raw:
        return []
    return [d.strip().lstrip("@").lower() for d in raw.split(",") if d.strip()]


def _google_client_config() -> dict:
    """Build the google-auth-oauthlib client config from env or JSON file."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_google_redirect_uri()],
            }
        }
    path = os.environ.get("OAUTH_CONFIG_PATH")
    if not path:
        raise RuntimeError(
            "Google OAuth not configured. Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET, "
            "or OAUTH_CONFIG_PATH pointing to a client_secret.json."
        )
    with open(path) as f:
        return json.load(f)


def _make_google_flow(state: Optional[str] = None) -> Flow:
    flow = Flow.from_client_config(
        _google_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=_google_redirect_uri(),
        state=state,
    )
    return flow


def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method != "S256":
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, code_challenge)


def _oauth_error(error: str, description: str = "", status: int = 400) -> JSONResponse:
    body = {"error": error}
    if description:
        body["error_description"] = description
    return JSONResponse(body, status_code=status)


# ---------- Discovery ----------

@router.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    base = _base_url()
    return JSONResponse({
        "resource": _canonical_resource(),
        "authorization_servers": [base],
        "scopes_supported": ADVERTISED_SCOPES,
        "bearer_methods_supported": ["header"],
    })


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    base = _base_url()
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ADVERTISED_SCOPES,
    })


# ---------- Dynamic Client Registration (RFC 7591) ----------

@router.post("/oauth/register")
async def register_client(request: Request):
    try:
        body = await request.json()
    except Exception:
        return _oauth_error("invalid_client_metadata", "Body must be JSON")

    redirect_uris = body.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return _oauth_error("invalid_redirect_uri", "redirect_uris must be a non-empty array")

    for uri in redirect_uris:
        if not isinstance(uri, str):
            return _oauth_error("invalid_redirect_uri", "redirect_uris must be strings")
        if not (uri.startswith("https://") or uri.startswith("http://localhost") or uri.startswith("http://127.0.0.1")):
            return _oauth_error("invalid_redirect_uri", f"redirect_uri must be https or localhost: {uri}")

    client_name = body.get("client_name", "Unnamed MCP Client")
    metadata = {k: v for k, v in body.items() if k not in {"redirect_uris", "client_name"}}

    record = token_store.register_client(redirect_uris, client_name, metadata)
    logger.info(f"Registered OAuth client {record['client_id']} ({client_name})")
    return JSONResponse(record, status_code=201)


# ---------- Authorization endpoint ----------

@router.get("/oauth/authorize")
async def authorize(request: Request):
    qp = request.query_params
    response_type = qp.get("response_type")
    client_id = qp.get("client_id")
    redirect_uri = qp.get("redirect_uri")
    code_challenge = qp.get("code_challenge")
    code_challenge_method = qp.get("code_challenge_method")
    client_state = qp.get("state", "")
    scope = qp.get("scope", " ".join(ADVERTISED_SCOPES))
    resource = qp.get("resource")

    if response_type != "code":
        return _oauth_error("unsupported_response_type", "Only 'code' is supported")

    if not client_id:
        return _oauth_error("invalid_request", "client_id is required")

    client = token_store.get_client(client_id)
    if not client:
        return _oauth_error("invalid_client", "Unknown client_id", status=401)

    if not redirect_uri or redirect_uri not in client["redirect_uris"]:
        return _oauth_error("invalid_request", "redirect_uri not registered")

    if not code_challenge or code_challenge_method != "S256":
        return _oauth_error("invalid_request", "PKCE with S256 is required")

    canonical = _canonical_resource()
    if resource and resource.rstrip("/") != canonical.rstrip("/"):
        return _oauth_error("invalid_target", f"resource must be {canonical}")
    resource = canonical

    flow = _make_google_flow()
    our_state = secrets.token_urlsafe(32)
    google_auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=our_state,
    )

    token_store.save_pending_authorization(
        state=our_state,
        client_id=client_id,
        redirect_uri=redirect_uri,
        client_state=client_state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
        scope=scope,
        google_code_verifier=flow.code_verifier,
    )

    return RedirectResponse(google_auth_url)


# ---------- Google OAuth callback ----------

@router.get("/auth/callback")
async def google_callback(request: Request):
    qp = request.query_params
    error = qp.get("error")
    code = qp.get("code")
    state = qp.get("state")

    if error:
        return HTMLResponse(
            f"<h2>Google login cancelled</h2><p>{error}</p>",
            status_code=400,
        )

    if not state or not code:
        return HTMLResponse("<h2>Missing state or code</h2>", status_code=400)

    pending = token_store.consume_pending_authorization(state)
    if not pending:
        return HTMLResponse(
            "<h2>This authorization request has expired or already been used.</h2>"
            "<p>Please retry the connect flow from your MCP client.</p>",
            status_code=400,
        )

    flow = _make_google_flow(state=state)
    flow.code_verifier = pending["google_code_verifier"]
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.exception("Google token exchange failed")
        return HTMLResponse(f"<h2>Google token exchange failed</h2><p>{e}</p>", status_code=502)

    creds = flow.credentials

    user_info_resp = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    if user_info_resp.status_code != 200:
        return HTMLResponse("<h2>Could not read your Google profile.</h2>", status_code=502)
    email = (user_info_resp.json() or {}).get("email", "")

    domains = _allowed_domains()
    if domains:
        email_domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
        if email_domain not in domains:
            return HTMLResponse(
                f"<h2>Access denied</h2>"
                f"<p>Only the following domains may connect: <strong>{', '.join(domains)}</strong></p>"
                f"<p>You signed in as: {email or '(unknown)'}</p>",
                status_code=403,
            )

    save_token(email, creds)
    logger.info(f"Stored Google credentials for {email}")

    our_code = token_store.create_auth_code(
        client_id=pending["client_id"],
        redirect_uri=pending["redirect_uri"],
        code_challenge=pending["code_challenge"],
        code_challenge_method=pending["code_challenge_method"],
        resource=pending["resource"],
        scope=pending["scope"],
        user_email=email,
    )

    params = {"code": our_code}
    if pending.get("client_state"):
        params["state"] = pending["client_state"]
    sep = "&" if "?" in pending["redirect_uri"] else "?"
    return RedirectResponse(f"{pending['redirect_uri']}{sep}{urlencode(params)}")


# ---------- Token endpoint ----------

@router.post("/oauth/token")
async def token(request: Request):
    form = await request.form()
    grant_type = form.get("grant_type")

    if grant_type == "authorization_code":
        return await _token_authorization_code(form)
    if grant_type == "refresh_token":
        return await _token_refresh(form)
    return _oauth_error("unsupported_grant_type", f"Unsupported grant_type: {grant_type}")


async def _token_authorization_code(form) -> JSONResponse:
    code = form.get("code")
    client_id = form.get("client_id")
    redirect_uri = form.get("redirect_uri")
    code_verifier = form.get("code_verifier")
    resource = form.get("resource")

    if not code or not client_id or not redirect_uri or not code_verifier:
        return _oauth_error("invalid_request", "Missing required fields")

    record = token_store.consume_auth_code(code)
    if not record:
        return _oauth_error("invalid_grant", "Authorization code invalid or expired")

    if record["client_id"] != client_id:
        return _oauth_error("invalid_grant", "client_id does not match")
    if record["redirect_uri"] != redirect_uri:
        return _oauth_error("invalid_grant", "redirect_uri does not match")

    if not _verify_pkce(code_verifier, record["code_challenge"], record["code_challenge_method"]):
        return _oauth_error("invalid_grant", "PKCE verification failed")

    canonical = _canonical_resource()
    if resource and resource.rstrip("/") != canonical.rstrip("/"):
        return _oauth_error("invalid_target", f"resource must be {canonical}")

    pair = token_store.issue_token_pair(
        client_id=client_id,
        user_email=record["user_email"],
        resource=record["resource"],
        scope=record["scope"],
    )
    return JSONResponse(pair)


async def _token_refresh(form) -> JSONResponse:
    refresh_token = form.get("refresh_token")
    client_id = form.get("client_id")

    if not refresh_token or not client_id:
        return _oauth_error("invalid_request", "Missing required fields")

    record = token_store.consume_refresh_token(refresh_token)
    if not record:
        return _oauth_error("invalid_grant", "Refresh token invalid or expired")
    if record["client_id"] != client_id:
        return _oauth_error("invalid_grant", "client_id does not match")

    pair = token_store.issue_token_pair(
        client_id=client_id,
        user_email=record["user_email"],
        resource=record["resource"],
        scope=record["scope"],
    )
    return JSONResponse(pair)


# ---------- Bearer resolution (used by middleware in main.py) ----------

def resolve_bearer(access_token: str) -> Optional[dict]:
    """Return the access-token record if valid for this resource, else None."""
    record = token_store.lookup_access_token(access_token)
    if not record:
        return None
    if record.get("resource", "").rstrip("/") != _canonical_resource().rstrip("/"):
        return None
    return record
