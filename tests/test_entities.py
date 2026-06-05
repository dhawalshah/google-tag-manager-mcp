from gtm import client
from gtm.tags import gtm_tag
from gtm.triggers import gtm_trigger
from gtm.variables import gtm_variable
from gtm.clients import gtm_client
from gtm.zones import gtm_zone
from gtm.transformations import gtm_transformation

WS = "accounts/1/containers/2/workspaces/3"


def test_tag_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {"tag": []})
    out = gtm_tag(action="list", parent=WS)
    assert out["success"] is True
    assert seen["p"] == f"{WS}/tags"


def test_tag_remove_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_tag(action="remove", path=f"{WS}/tags/9")
    assert out["success"] is False and "confirm=true" in out["error"]


def test_tag_remove_with_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m) or {})
    out = gtm_tag(action="remove", path=f"{WS}/tags/9", confirm=True)
    assert out["success"] is True and seen["m"] == "DELETE"


def test_trigger_revert_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_trigger(action="revert", path=f"{WS}/triggers/5")
    assert out["success"] is False and "confirm=true" in out["error"]


def test_all_six_list_use_their_collection(monkeypatch):
    cases = [
        (gtm_tag, "tags"), (gtm_trigger, "triggers"), (gtm_variable, "variables"),
        (gtm_client, "clients"), (gtm_zone, "zones"), (gtm_transformation, "transformations"),
    ]
    for fn, collection in cases:
        seen = {}
        monkeypatch.setattr(client, "request",
                            lambda m, p, params=None, body=None: seen.update(p=p) or {})
        out = fn(action="list", parent=WS)
        assert out["success"] is True
        assert seen["p"] == f"{WS}/{collection}", f"{fn.__name__} -> {seen['p']}"
