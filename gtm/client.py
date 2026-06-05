"""Shared GTM API client: request helpers, throttle+backoff, formatter, dispatcher."""
import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import requests

from oauth.google_auth import get_headers_with_auto_token, current_user_email

logger = logging.getLogger("gtm_audit")

GTM_BASE = "https://tagmanager.googleapis.com/tagmanager/v2"


def format_response(data, resource: str = "", **metadata) -> dict:
    md = {"resource": resource, "timestamp": datetime.now(timezone.utc).isoformat()}
    md.update(metadata)
    return {"success": True, "data": data, "metadata": md, "error": None}


def format_error(message: str, error_code: str = "API_ERROR") -> dict:
    return {
        "success": False,
        "data": None,
        "error": message,
        "error_code": error_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class Throttle:
    """Sliding-window rate limiter. Default tuned under GTM's ~0.25 QPS quota."""

    def __init__(self, max_calls: int = 12, window: float = 100.0):
        self.max_calls = max_calls
        self.window = window
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.time()
            while self._calls and now - self._calls[0] >= self.window:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                wait = self.window - (now - self._calls[0])
                if wait > 0:
                    time.sleep(wait)
                now = time.time()
                while self._calls and now - self._calls[0] >= self.window:
                    self._calls.popleft()
            self._calls.append(time.time())


_throttle = Throttle()

MAX_RETRIES = 4
BACKOFF_BASE = 1.0


def _audit(method: str, path: str):
    logger.info(json.dumps({
        "method": method,
        "path": path,
        "user": current_user_email.get() or "local",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))


def request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Make a throttled, retrying GTM API request. `path` is appended to GTM_BASE."""
    _audit(method, path)
    headers = get_headers_with_auto_token()
    if body is not None:
        headers["Content-Type"] = "application/json"
    url = f"{GTM_BASE}/{path.lstrip('/')}"
    for attempt in range(MAX_RETRIES):
        _throttle.acquire()
        resp = requests.request(method, url, headers=headers, params=params, json=body)
        if resp.status_code in (429,) or (resp.status_code == 403 and b"rateLimitExceeded" in resp.content):
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE * (2 ** attempt))
                continue
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    raise RuntimeError("GTM API rate limit: exhausted retries")
