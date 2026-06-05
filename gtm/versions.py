"""gtm_version — Container versions (get, live, publish, set_latest, undelete, update, remove)."""
from gtm import client
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="version",
    collection="versions",
    actions={"get", "live", "publish", "set_latest", "undelete", "update", "remove"},
    destructive={"publish", "set_latest", "undelete", "remove"},
    special={"live": "GET", "publish": "POST", "set_latest": "POST", "undelete": "POST"},
)


def gtm_version(action: str, parent: str | None = None, path: str | None = None,
                config: dict | None = None, confirm: bool = False,
                params: dict | None = None) -> dict:
    """Manage GTM container versions.

    Actions:
      - get:        path='<container>/versions/{id}'.
      - live:       path='<container>' (or parent='<container>') -> currently-published version. (read-only)
      - publish:    path='<container>/versions/{id}', confirm=true. PUSHES LIVE. (destructive)
      - set_latest: path='<container>/versions/{id}', confirm=true. (destructive)
      - undelete:   path='<container>/versions/{id}', confirm=true. (destructive)
      - update:     path='<container>/versions/{id}', config={...}.
      - remove:     path='<container>/versions/{id}', confirm=true. (destructive)
    """
    if action == "live":
        container = path or parent
        if not container:
            return client.format_error("'live' requires the container path.", "MISSING_PATH")
        return dispatch(SPEC, action="live", path=f"{container}/versions", params=params)
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
