from gtm import client
from gtm.containers import gtm_container
from gtm.workspaces import gtm_workspace

ACC = "accounts/1"
CON = "accounts/1/containers/2"
WS = "accounts/1/containers/2/workspaces/3"


def test_container_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(p=p) or {"container": []})
    out = gtm_container(action="list", parent=ACC)
    assert seen["p"] == f"{ACC}/containers" and out["success"]


def test_container_combine_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_container(action="combine", path=CON)
    assert out["success"] is False and "confirm=true" in out["error"]


def test_container_snippet_readonly_get(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_container(action="snippet", path=CON)
    assert out["success"] is True and seen["m"] == "GET" and seen["p"] == f"{CON}:snippet"


def test_container_lookup_uses_root_path(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p, params=params) or {})
    out = gtm_container(action="lookup", params={"destinationId": "G-1"})
    assert out["success"] is True
    assert seen["m"] == "GET" and seen["p"] == "accounts/containers:lookup"
    assert seen["params"] == {"destinationId": "G-1"}


def test_container_move_tag_id_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_container(action="move_tag_id", path=CON)
    assert out["success"] is False and "confirm=true" in out["error"]


def test_workspace_create_version_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_workspace(action="create_version", path=WS)
    assert out["success"] is False and "confirm=true" in out["error"]


def test_workspace_create_version_with_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_workspace(action="create_version", path=WS, confirm=True, config={"name": "v"})
    assert out["success"] is True
    assert seen["m"] == "POST" and seen["p"] == f"{WS}:create_version"


def test_workspace_sync_post_and_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_workspace(action="sync", path=WS, confirm=True)
    assert out["success"] is True and seen["m"] == "POST" and seen["p"] == f"{WS}:sync"


def test_workspace_quick_preview_no_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_workspace(action="quick_preview", path=WS)
    assert out["success"] is True and seen["m"] == "POST" and seen["p"] == f"{WS}:quick_preview"


def test_workspace_get_status_slash_path(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {"workspace": {}})
    out = gtm_workspace(action="get_status", path=WS)
    assert out["success"] is True
    assert seen["m"] == "GET" and seen["p"] == f"{WS}/status"
