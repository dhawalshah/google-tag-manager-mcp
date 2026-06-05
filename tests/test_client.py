from gtm import client


def test_format_response_envelope():
    out = client.format_response({"id": "1"}, resource="tags")
    assert out["success"] is True
    assert out["data"] == {"id": "1"}
    assert out["error"] is None
    assert out["metadata"]["resource"] == "tags"
    assert "timestamp" in out["metadata"]


def test_format_error_envelope():
    out = client.format_error("nope", error_code="BAD")
    assert out["success"] is False
    assert out["data"] is None
    assert out["error"] == "nope"
    assert out["error_code"] == "BAD"


def test_throttle_blocks_when_over_rate(monkeypatch):
    # Simulate clock so we don't actually sleep.
    fake = {"t": 1000.0}
    sleeps = []
    monkeypatch.setattr(client.time, "time", lambda: fake["t"])
    monkeypatch.setattr(client.time, "sleep", lambda s: (sleeps.append(s), fake.__setitem__("t", fake["t"] + s)))
    t = client.Throttle(max_calls=2, window=10.0)
    t.acquire(); t.acquire()       # 2 calls, fills window
    t.acquire()                    # 3rd must wait for window to free
    assert sleeps and sleeps[0] > 0


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}
        self.content = b"x" if payload is not None else b""
        self.headers = {}
    def json(self): return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            raise client.requests.HTTPError(f"{self.status_code}")


def test_request_retries_on_429_then_succeeds(monkeypatch):
    calls = {"n": 0}
    def fake_request(method, url, headers=None, params=None, json=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(429)
        return _Resp(200, {"ok": True})
    monkeypatch.setattr(client.requests, "request", fake_request)
    monkeypatch.setattr(client, "get_headers_with_auto_token", lambda: {"Authorization": "Bearer x"})
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    monkeypatch.setattr(client, "_throttle", client.Throttle(max_calls=999, window=1.0))
    out = client.request("GET", "accounts/1")
    assert out == {"ok": True}
    assert calls["n"] == 2
