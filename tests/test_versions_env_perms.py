from gtm import client
from gtm.versions import gtm_version
from gtm.version_headers import gtm_version_header
from gtm.environments import gtm_environment
from gtm.destinations import gtm_destination
from gtm.user_permissions import gtm_user_permission

CON = "accounts/1/containers/2"
VER = "accounts/1/containers/2/versions/9"
ACC = "accounts/1"


def test_version_publish_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_version(action="publish", path=VER)
    assert out["success"] is False and "confirm=true" in out["error"]


def test_version_publish_with_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_version(action="publish", path=VER, confirm=True)
    assert out["success"] is True and seen["m"] == "POST" and seen["p"] == f"{VER}:publish"


def test_version_live_slash_get(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_version(action="live", path=CON)
    assert out["success"] is True and seen["m"] == "GET" and seen["p"] == f"{CON}/live"


def test_version_set_latest_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_version(action="set_latest", path=VER)
    assert out["success"] is False and "confirm=true" in out["error"]


def test_version_header_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(p=p) or {})
    out = gtm_version_header(action="list", parent=CON)
    assert out["success"] is True and seen["p"] == f"{CON}/version_headers"


def test_version_header_latest(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_version_header(action="latest", parent=CON)
    assert out["success"] is True and seen["m"] == "GET" and seen["p"] == f"{CON}/version_headers:latest"


def test_environment_reauthorize_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_environment(action="reauthorize", path=f"{CON}/environments/4")
    assert out["success"] is False and "confirm=true" in out["error"]


def test_environment_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(p=p) or {})
    out = gtm_environment(action="list", parent=CON)
    assert out["success"] is True and seen["p"] == f"{CON}/environments"


def test_destination_link_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_destination(action="link", parent=CON, params={"destinationId": "G-1"})
    assert out["success"] is False and "confirm=true" in out["error"]


def test_destination_link_with_confirm_path(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_destination(action="link", parent=CON, params={"destinationId": "G-1"}, confirm=True)
    assert out["success"] is True and seen["m"] == "POST" and seen["p"] == f"{CON}/destinations:link"


def test_destination_rejects_unlink():
    out = gtm_destination(action="unlink", path=f"{CON}/destinations/9")
    assert out["success"] is False and "Unknown action" in out["error"]


def test_user_permission_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(p=p) or {"userPermission": []})
    out = gtm_user_permission(action="list", parent=ACC)
    assert out["success"] is True and seen["p"] == f"{ACC}/user_permissions"
