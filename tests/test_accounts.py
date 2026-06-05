from gtm import client
from gtm.accounts import gtm_account


def test_account_list(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(method=m, path=p) or {"account": []})
    out = gtm_account(action="list")
    assert out["success"] is True
    assert seen["path"] == "accounts"


def test_account_update_requires_no_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda m, p, params=None, body=None: {"name": "x"})
    out = gtm_account(action="update", path="accounts/1", config={"name": "x"})
    assert out["success"] is True


def test_account_rejects_create():
    out = gtm_account(action="create", parent="accounts")
    assert out["success"] is False
    assert "Unknown action" in out["error"]
