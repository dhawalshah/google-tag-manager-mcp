"""Per-user OAuth token storage in Firestore."""
import json
import os
import logging
from google.cloud import firestore
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

logger = logging.getLogger(__name__)
COLLECTION = "user_tokens_gtm"


def _db():
    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        raise RuntimeError("GCP_PROJECT_ID environment variable is not set.")
    return firestore.Client(project=project)


def save_token(user_email: str, creds: Credentials):
    _db().collection(COLLECTION).document(user_email).set({
        "token_json": creds.to_json(),
        "updated_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info(f"Saved token for {user_email}")


def load_token(user_email: str, scopes: list):
    doc = _db().collection(COLLECTION).document(user_email).get()
    if not doc.exists:
        logger.warning(f"No token found for {user_email}")
        return None
    token_json = doc.to_dict().get("token_json")
    creds = Credentials.from_authorized_user_info(json.loads(token_json), scopes)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            logger.info(f"Refreshing token for {user_email}")
            creds.refresh(Request())
            save_token(user_email, creds)
            return creds
        except RefreshError:
            logger.warning(f"Token refresh failed for {user_email} — re-login required")
            return None
    return None
