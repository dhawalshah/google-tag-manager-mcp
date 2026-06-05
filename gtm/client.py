"""Shared GTM API client: request helpers, throttle+backoff, formatter, dispatcher."""
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
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


@dataclass
class ResourceSpec:
    name: str
    collection: str
    actions: set
    destructive: set = field(default_factory=set)
    # special verb actions → HTTP method, e.g. {"publish": "POST", "sync": "POST"}
    special: dict = field(default_factory=dict)

    def __post_init__(self):
        routable = set(_STD) | set(self.special)
        unroutable = self.actions - routable
        if unroutable:
            raise ValueError(
                f"{self.name}: actions not routable via _STD or special: {sorted(unroutable)}"
            )
        orphaned = self.destructive - (self.actions | set(self.special))
        if orphaned:
            raise ValueError(
                f"{self.name}: destructive actions not in actions/special: {sorted(orphaned)}"
            )


# Standard CRUD action → HTTP method. Routing (parent vs path) is decided in dispatch().
_STD = {
    "list":   "GET",
    "get":    "GET",
    "create": "POST",
    "update": "PUT",
    "remove": "DELETE",
    "revert": "POST",
}


def dispatch(spec: ResourceSpec, *, action: str, parent: str | None = None,
             path: str | None = None, config: dict | None = None,
             confirm: bool = False, params: dict | None = None) -> dict:
    """Validate + route a consolidated tool call to the GTM API."""
    if action not in spec.actions:
        return format_error(
            f"Unknown action '{action}' for {spec.name}. "
            f"Valid actions: {', '.join(sorted(spec.actions))}.",
            error_code="UNKNOWN_ACTION",
        )
    if action in spec.destructive and not confirm:
        return format_error(
            f"Action '{action}' on {spec.name} is destructive and may affect "
            f"live production. Re-call with confirm=true to proceed.",
            error_code="CONFIRMATION_REQUIRED",
        )
    try:
        if action in spec.special:
            method = spec.special[action]
            if not path:
                return format_error(f"'{action}' requires a path.", "MISSING_PATH")
            data = request(method, f"{path}:{action}", params=params, body=config)
        elif action in _STD:
            method = _STD[action]
            if action == "list":
                if not parent:
                    return format_error("'list' requires a parent path.", "MISSING_PARENT")
                data = request(method, f"{parent}/{spec.collection}", params=params)
            elif action == "create":
                if not parent:
                    return format_error("'create' requires a parent path.", "MISSING_PARENT")
                data = request(method, f"{parent}/{spec.collection}", body=config)
            elif action == "revert":
                if not path:
                    return format_error("'revert' requires a path.", "MISSING_PATH")
                data = request("POST", f"{path}:revert", params=params)
            else:  # get / update / remove
                if not path:
                    return format_error(f"'{action}' requires a path.", "MISSING_PATH")
                data = request(method, path, params=params, body=config)
        else:
            return format_error(f"Action '{action}' not routable for {spec.name}.", "UNROUTABLE")
        return format_response(data, resource=spec.name)
    except requests.RequestException as e:
        return format_error(str(e), error_code="API_ERROR")
