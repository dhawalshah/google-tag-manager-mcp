"""gtm_version — Container versions (get, live, publish, set_latest, undelete, update, remove)."""
from gtm import client
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="version",
    collection="versions",
    actions={"get", "live", "publish", "set_latest", "undelete", "update", "remove"},
    destructive={"publish", "set_latest", "undelete", "remove"},
    special={"publish": "POST", "set_latest": "POST", "undelete": "POST"},
    custom={"live"},
)


def gtm_version(action: str, parent: str | None = None, path: str | None = None,
                config: dict | None = None, confirm: bool = False,
                params: dict | None = None) -> dict:
    """Manage GTM container versions.

    Actions:
      - get:        path='<container>/versions/{id}'.
      - live:       path='<container>' -> currently-published version. (read-only)
      - publish:    path='<container>/versions/{id}', confirm=true. PUSHES LIVE. (destructive)
      - set_latest: path='<container>/versions/{id}', confirm=true. (destructive)
      - undelete:   path='<container>/versions/{id}', confirm=true. (destructive)
      - update:     path='<container>/versions/{id}', config={...}.
      - remove:     path='<container>/versions/{id}', confirm=true. (destructive)
    """
    if action == "live":
        if not path:
            return client.format_error("'live' requires a path (the container).", "MISSING_PATH")
        try:
            return client.format_response(client.request("GET", f"{path}/live"), resource="version")
        except client.requests.RequestException as e:
            return client.format_error(str(e), error_code="API_ERROR")
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
