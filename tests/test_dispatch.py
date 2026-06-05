import pytest
from gtm import client
from gtm.client import ResourceSpec


SPEC = ResourceSpec(
    name="tag",
    collection="tags",
    actions={"list", "get", "create", "update", "remove", "revert"},
    destructive={"remove", "revert"},
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
