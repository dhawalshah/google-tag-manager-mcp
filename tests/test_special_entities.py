from gtm import client
from gtm.builtin_variables import gtm_built_in_variable
from gtm.folders import gtm_folder
from gtm.templates import gtm_template
from gtm.gtag_config import gtm_gtag_config

WS = "accounts/1/containers/2/workspaces/3"


def test_builtin_create_forwards_type(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(p=p, params=params) or {})
    out = gtm_built_in_variable(action="create", parent=WS, params={"type": "pageUrl"})
    assert out["success"] is True
    assert seen["p"] == f"{WS}/built_in_variables"
    assert seen["params"] == {"type": "pageUrl"}


def test_builtin_remove_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_built_in_variable(action="remove", path=f"{WS}/built_in_variables", params={"type": "pageUrl"})
    assert out["success"] is False and "confirm=true" in out["error"]


def test_folder_entities_action(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_folder(action="entities", path=f"{WS}/folders/7")
    assert out["success"] is True
    assert seen["m"] == "POST" and seen["p"] == f"{WS}/folders/7:entities"


def test_folder_move_entities_needs_confirm(monkeypatch):
    monkeypatch.setattr(client, "request", lambda *a, **k: {})
    out = gtm_folder(action="move_entities_to_folder", path=f"{WS}/folders/7", params={"tagId": "1"})
    assert out["success"] is False and "confirm=true" in out["error"]


def test_folder_move_entities_with_confirm(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_folder(action="move_entities_to_folder", path=f"{WS}/folders/7",
                     params={"tagId": "1"}, confirm=True)
    assert out["success"] is True
    assert seen["m"] == "POST" and seen["p"] == f"{WS}/folders/7:move_entities_to_folder"


def test_template_import_from_gallery_translates_parent(monkeypatch):
    seen = {}
    monkeypatch.setattr(client, "request",
                        lambda m, p, params=None, body=None: seen.update(m=m, p=p) or {})
    out = gtm_template(action="import_from_gallery", parent=WS, confirm=True, config={})
    assert out["success"] is True
    assert seen["m"] == "POST" and seen["p"] == f"{WS}/templates:import_from_gallery"


def test_gtag_config_no_revert():
    out = gtm_gtag_config(action="revert", path=f"{WS}/gtag_config/1")
    assert out["success"] is False and "Unknown action" in out["error"]
