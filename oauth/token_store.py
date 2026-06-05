"""
Firestore-backed storage for the embedded OAuth 2.1 authorization server.

Collections:
  oauth_clients/{client_id}        — DCR client registrations
  oauth_pending/{state}            — pending authorize → Google round-trip
  oauth_codes/{code}               — issued authorization codes (single-use)
  oauth_tokens/{access_token}      — issued bearer access tokens
  oauth_refresh/{refresh_token}    — issued refresh tokens

All records carry an `expires_at` timestamp. Reads check expiry and treat
expired records as missing. A periodic cleanup is not required for correctness.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)

CLIENTS = "oauth_clients"
PENDING = "oauth_pending"
CODES = "oauth_codes"
ACCESS = "oauth_tokens"
REFRESH = "oauth_refresh"

PENDING_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)


def _db():
    return firestore.Client(project=os.environ["GCP_PROJECT_ID"])


def _now():
    return datetime.now(timezone.utc)


def _expired(doc) -> bool:
    exp = doc.get("expires_at")
    if exp is None:
        return False
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp < _now()
    return False


def _new_token(prefix: str, nbytes: int = 32) -> str:
    return f"{prefix}_{secrets.token_urlsafe(nbytes)}"


# ---------- Clients (DCR) ----------

def register_client(redirect_uris: list[str], client_name: str, metadata: dict) -> dict:
    client_id = _new_token("mcp_client", nbytes=16)
    record = {
        "client_id": client_id,
        "redirect_uris": redirect_uris,
        "client_name": client_name,
        "metadata": metadata,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    _db().collection(CLIENTS).document(client_id).set(record)
    return {
        "client_id": client_id,
        "client_id_issued_at": int(_now().timestamp()),
        "redirect_uris": redirect_uris,
        "client_name": client_name,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        **metadata,
    }


def get_client(client_id: str) -> Optional[dict]:
    doc = _db().collection(CLIENTS).document(client_id).get()
    return doc.to_dict() if doc.exists else None


# ---------- Pending authorizations (state for Google round trip) ----------

def save_pending_authorization(*, state: str, client_id: str, redirect_uri: str, client_state: str,
                               code_challenge: str, code_challenge_method: str,
                               resource: str, scope: str,
                               google_code_verifier: str) -> None:
    _db().collection(PENDING).document(state).set({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "client_state": client_state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "scope": scope,
        "google_code_verifier": google_code_verifier,
        "expires_at": _now() + PENDING_TTL,
    })


def consume_pending_authorization(state: str) -> Optional[dict]:
    ref = _db().collection(PENDING).document(state)
    doc = ref.get()
    if not doc.exists:
        return None
    if _expired(doc):
        ref.delete()
        return None
    data = doc.to_dict()
    ref.delete()
    return data


# ---------- Authorization codes ----------

def create_auth_code(*, client_id: str, redirect_uri: str, code_challenge: str,
                     code_challenge_method: str, resource: str, scope: str,
                     user_email: str) -> str:
    code = _new_token("mcp_ac")
    _db().collection(CODES).document(code).set({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "scope": scope,
        "user_email": user_email,
        "expires_at": _now() + CODE_TTL,
    })
    return code


def consume_auth_code(code: str) -> Optional[dict]:
    ref = _db().collection(CODES).document(code)
    doc = ref.get()
    if not doc.exists:
        return None
    if _expired(doc):
        ref.delete()
        return None
    data = doc.to_dict()
    ref.delete()
    return data


# ---------- Access + refresh tokens ----------

def issue_token_pair(*, client_id: str, user_email: str, resource: str, scope: str) -> dict:
    access = _new_token("mcp_at")
    refresh = _new_token("mcp_rt")
    now = _now()
    access_expires = now + ACCESS_TTL
    refresh_expires = now + REFRESH_TTL
    _db().collection(ACCESS).document(access).set({
        "client_id": client_id,
        "user_email": user_email,
        "resource": resource,
        "scope": scope,
        "expires_at": access_expires,
    })
    _db().collection(REFRESH).document(refresh).set({
        "client_id": client_id,
        "user_email": user_email,
        "resource": resource,
        "scope": scope,
        "expires_at": refresh_expires,
    })
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TTL.total_seconds()),
        "refresh_token": refresh,
        "scope": scope,
    }


def lookup_access_token(access_token: str) -> Optional[dict]:
    doc = _db().collection(ACCESS).document(access_token).get()
    if not doc.exists or _expired(doc):
        return None
    return doc.to_dict()


def consume_refresh_token(refresh_token: str) -> Optional[dict]:
    """Read-and-rotate: refresh tokens are single use (OAuth 2.1 §4.3.1)."""
    ref = _db().collection(REFRESH).document(refresh_token)
    doc = ref.get()
    if not doc.exists or _expired(doc):
        return None
    data = doc.to_dict()
    ref.delete()
    return data
