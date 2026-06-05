"""
Google Tag Manager MCP Server.

The MCP endpoint at /mcp is an OAuth 2.1 protected resource. The server
also acts as the authorization server for it (see oauth/oauth_server.py),
proxying user authentication to Google.

Auth flow for MCP clients (Claude, etc.):

  1. Client GETs /mcp without a token → 401 + WWW-Authenticate
  2. Client follows the protected-resource metadata link, registers with
     the authorization server (Dynamic Client Registration), and runs the
     OAuth 2.1 authorization code flow with PKCE.
  3. Client receives an opaque bearer issued by this server and includes
     it on every /mcp request.
  4. Middleware here validates the bearer, looks up the user's stored
     Google credentials, and sets a ContextVar consumed by the GTM tools.
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse

from server import mcp
from oauth.oauth_server import router as oauth_router, resolve_bearer
from oauth.google_auth import current_user_email

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

mcp_asgi_app = mcp.http_app(path="/mcp")
app = FastAPI(lifespan=mcp_asgi_app.lifespan, redirect_slashes=False)

app.include_router(oauth_router)


@app.get("/")
async def root():
    base = os.environ.get("BASE_URL", "").rstrip("/")
    return JSONResponse({
        "name": "Google Tag Manager MCP",
        "mcp_endpoint": f"{base}/mcp" if base else "/mcp",
        "protected_resource_metadata": f"{base}/.well-known/oauth-protected-resource",
    })


def _unauthorized() -> Response:
    base = os.environ.get("BASE_URL", "").rstrip("/")
    metadata_url = f"{base}/.well-known/oauth-protected-resource"
    return Response(
        content='{"error":"unauthorized"}',
        status_code=401,
        media_type="application/json",
        headers={
            "WWW-Authenticate": (
                f'Bearer realm="mcp", '
                f'resource_metadata="{metadata_url}", '
                f'error="invalid_token"'
            )
        },
    )


@app.middleware("http")
async def authenticate_mcp(request: Request, call_next):
    path = request.url.path
    if path != "/mcp" and not path.startswith("/mcp/"):
        return await call_next(request)

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return _unauthorized()

    access_token = auth.split(" ", 1)[1].strip()
    record = resolve_bearer(access_token)
    if not record:
        return _unauthorized()

    current_user_email.set(record["user_email"])
    return await call_next(request)


app.mount("/", mcp_asgi_app)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
