#!/usr/bin/env python3
"""
One-shot local authentication for Google Tag Manager MCP (STDIO mode).

Opens your browser for Google OAuth consent, saves token to
~/.config/gtm-mcp/token.json

Usage:
    python setup_local_auth.py

Requirements:
    OAUTH_CONFIG_PATH env var (or ./client_secret.json by default)
"""
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/tagmanager.readonly",
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.delete.containers",
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
    "https://www.googleapis.com/auth/tagmanager.publish",
    "https://www.googleapis.com/auth/tagmanager.manage.users",
]

REDIRECT_URI = "http://localhost:8080/auth/callback"
TOKEN_PATH = Path.home() / ".config" / "gtm-mcp" / "token.json"
CLIENT_CONFIG_PATH = os.environ.get("OAUTH_CONFIG_PATH", "./client_secret.json")

_auth_code = None
_auth_error = None
_server_done = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code, _auth_error
        parsed = urlparse(self.path)
        if parsed.path != "/auth/callback":
            self.send_response(404); self.end_headers(); return
        params = parse_qs(parsed.query)
        if "error" in params:
            _auth_error = params["error"][0]
            self._respond("<h2>Authentication cancelled.</h2>")
        elif "code" in params:
            _auth_code = params["code"][0]
            self._respond("<h2>Authentication successful! You can close this tab.</h2>")
        _server_done.set()

    def _respond(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args): pass


def main():
    if not Path(CLIENT_CONFIG_PATH).exists():
        print(f"ERROR: OAuth credentials file not found: {CLIENT_CONFIG_PATH}")
        raise SystemExit(1)

    flow = Flow.from_client_secrets_file(CLIENT_CONFIG_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("Opening browser for Google authentication...")
    print(f"If browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    _server_done.wait(timeout=120)
    server.shutdown()

    if _auth_error:
        print(f"ERROR: {_auth_error}"); raise SystemExit(1)
    if not _auth_code:
        print("ERROR: No code received (timed out)."); raise SystemExit(1)

    flow.fetch_token(code=_auth_code)
    creds = flow.credentials
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"\nToken saved to: {TOKEN_PATH}")
    print("\nAdd to Claude Desktop MCP config in claude_desktop_config.json:")
    print("""
  "google-tag-manager": {
    "command": "python",
    "args": ["/path/to/gtm-mcp/server.py"],
    "env": {
      "OAUTH_CONFIG_PATH": "/path/to/client_secret.json",
      "MCP_USER_EMAIL": "you@company.com"
    }
  }
""")


if __name__ == "__main__":
    main()
