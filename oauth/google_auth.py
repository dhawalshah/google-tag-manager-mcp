"""GTM OAuth authentication — HTTP server mode (Firestore) and STDIO local mode."""
import json
import os
import contextvars
import logging
from pathlib import Path
from typing import Dict, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from .firestore_tokens import load_token

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.readonly",
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.delete.containers",
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
    "https://www.googleapis.com/auth/tagmanager.publish",
    "https://www.googleapis.com/auth/tagmanager.manage.users",
]

LOCAL_TOKEN_PATH = Path.home() / ".config" / "gtm-mcp" / "token.json"

current_user_email: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user_email", default=None
)


def load_local_token(scopes: list) -> Optional[Credentials]:
    if not LOCAL_TOKEN_PATH.exists():
        logger.warning(f"Local token file not found: {LOCAL_TOKEN_PATH}")
        return None
    try:
        token_data = json.loads(LOCAL_TOKEN_PATH.read_text())
        creds = Credentials.from_authorized_user_info(token_data, scopes)
    except Exception as e:
        logger.warning(f"Failed to load local token: {e}")
        return None
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            LOCAL_TOKEN_PATH.write_text(creds.to_json())
            return creds
        except RefreshError:
            logger.warning("Local token refresh failed — re-run setup_local_auth.py")
            return None
    return None


def get_headers_with_auto_token() -> Dict[str, str]:
    email = current_user_email.get()
    if email:
        creds = load_token(email, SCOPES)
        if not creds:
            raise ValueError(
                f"No valid token for {email}. "
                "Reconnect this MCP server in your client to re-run the Google sign-in."
            )
        return {"Authorization": f"Bearer {creds.token}"}

    local_email = os.environ.get("MCP_USER_EMAIL")
    if local_email:
        creds = load_local_token(SCOPES)
        if not creds:
            raise ValueError("Local token invalid. Run: python setup_local_auth.py")
        return {"Authorization": f"Bearer {creds.token}"}

    raise ValueError(
        "No authenticated user. "
        "For local use: set MCP_USER_EMAIL in your Claude Desktop config and run setup_local_auth.py. "
        "For team server: reconnect from your MCP client to run the OAuth flow."
    )
