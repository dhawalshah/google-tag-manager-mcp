import pytest
from gtm import client
from gtm.client import ResourceSpec


SPEC = ResourceSpec(
    name="tag",
    collection="tags",
    actions={"list", "get", "create", "update", "remove", "revert"},
    destructive={"remove", "revert"},
)

SPECIAL_SPEC = ResourceSpec(
    name="container",
    collection="containers",
    actions={"get", "list", "snippet", "publish"},
    destructive={"publish"},
    special={"snippet": "GET", "publish": "POST"},
)


def test_unknown_action_errors():
    out = client.dispatch(SPEC, action="frobnicate")
    assert out["success"] is False
    assert "frobnicate" in out["error"]
    assert "list" in out["error"]  # lists valid actions


def test_destructive_requires_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {"called": True})
    out = client.dispatch(SPEC, action="remove", path="accounts/1/containers/2/workspaces/3/tags/4")
    assert out["success"] is False
    assert "confirm=true" in out["error"]


def test_destructive_proceeds_with_confirm(monkeypatch):
    seen = {}
    def fake_request(method, path, params=None, body=None):
        seen["method"] = method; seen["path"] = path
        return {}
    monkeypatch.setattr(client, "request", fake_request)
    out = client.dispatch(SPEC, action="remove",
                          path="accounts/1/containers/2/workspaces/3/tags/4", confirm=True)
    assert out["success"] is True
    assert seen["method"] == "DELETE"


def test_list_calls_parent_collection(monkeypatch):
    seen = {}
    def fake_request(method, path, params=None, body=None):
        seen["method"] = method; seen["path"] = path
        return {"tag": [{"name": "t1"}]}
    monkeypatch.setattr(client, "request", fake_request)
    out = client.dispatch(SPEC, action="list",
                          parent="accounts/1/containers/2/workspaces/3")
    assert seen["method"] == "GET"
    assert seen["path"] == "accounts/1/containers/2/workspaces/3/tags"
    assert out["success"] is True


def test_create_routes_post_to_parent_collection(monkeypatch):
    seen = {}
    def fake_request(method, path, params=None, body=None):
        seen.update(method=method, path=path, body=body); return {}
    monkeypatch.setattr(client, "request", fake_request)
    out = client.dispatch(SPEC, action="create",
                          parent="accounts/1/containers/2/workspaces/3", config={"name": "t"})
    assert out["success"] is True
    assert seen["method"] == "POST"
    assert seen["path"] == "accounts/1/containers/2/workspaces/3/tags"
    assert seen["body"] == {"name": "t"}


def test_get_routes_to_full_path(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = client.dispatch(SPEC, action="get", path="accounts/1/containers/2/workspaces/3/tags/4")
    assert seen["m"] == "GET" and seen["p"].endswith("/tags/4")


def test_revert_routes_to_revert_verb(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = client.dispatch(SPEC, action="revert",
                          path="accounts/1/containers/2/workspaces/3/tags/4", confirm=True)
    assert seen["m"] == "POST"
    assert seen["p"] == "accounts/1/containers/2/workspaces/3/tags/4:revert"


def test_special_readonly_verb_no_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = client.dispatch(SPECIAL_SPEC, action="snippet", path="accounts/1/containers/2")
    assert out["success"] is True
    assert seen["m"] == "GET" and seen["p"] == "accounts/1/containers/2:snippet"


def test_special_destructive_verb_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = client.dispatch(SPECIAL_SPEC, action="publish", path="accounts/1/containers/2/versions/9")
    assert out["success"] is False and "confirm=true" in out["error"]


def test_missing_path_errors():
    out = client.dispatch(SPEC, action="get")
    assert out["success"] is False and out["error_code"] == "MISSING_PATH"


def test_missing_parent_on_create_errors():
    out = client.dispatch(SPEC, action="create", config={"name": "t"})
    assert out["success"] is False and out["error_code"] == "MISSING_PARENT"


def test_bad_spec_raises_at_construction():
    import pytest as _pytest
    with _pytest.raises(ValueError):
        ResourceSpec(name="bad", collection="bad", actions={"frobnicate"})


def test_create_forwards_params(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(params=params) or {})
    client.dispatch(SPEC, action="create", parent="accounts/1/containers/2/workspaces/3",
                    config={"x": 1}, params={"type": "pageUrl"})
    assert seen["params"] == {"type": "pageUrl"}


def test_custom_action_allowed_in_spec():
    spec = ResourceSpec(name="ws", collection="workspaces",
                        actions={"get", "get_status"}, custom={"get_status"})
    # constructing it must not raise; get_status is routable via custom
    assert "get_status" in spec.actions
