"""gtm_workspace — Workspaces (CRUD + create_version, get_status, sync, quick_preview, resolve_conflict)."""
from gtm import client
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="workspace",
    collection="workspaces",
    actions={"create", "get", "list", "update", "remove",
             "create_version", "get_status", "sync", "quick_preview", "resolve_conflict"},
    destructive={"remove", "create_version", "sync", "resolve_conflict"},
    special={"create_version": "POST", "sync": "POST",
             "quick_preview": "POST", "resolve_conflict": "POST"},
    custom={"get_status"},
)


def gtm_workspace(action: str, parent: str | None = None, path: str | None = None,
                  config: dict | None = None, confirm: bool = False,
                  params: dict | None = None) -> dict:
    """Manage GTM workspaces.

    Standard CRUD (list/create: parent=<container>; get/update/remove: path=<workspace>) plus:
      - create_version:   path=<workspace>, config={name,notes}, confirm=true. (destructive)
      - get_status:       path=<workspace> -> uncommitted changes. (read-only)
      - sync:             path=<workspace>, confirm=true. (destructive)
      - quick_preview:    path=<workspace> -> preview of unsubmitted changes. (read-only)
      - resolve_conflict: path=<workspace>, config={...}, confirm=true. (destructive)
    """
    if action == "get_status":
        if not path:
            return client.format_error("'get_status' requires a path.", "MISSING_PATH")
        try:
            return client.format_response(client.request("GET", f"{path}/status"), resource="workspace")
        except client.requests.RequestException as e:
            return client.format_error(str(e), error_code="API_ERROR")
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
