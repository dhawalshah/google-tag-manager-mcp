"""gtm_tag — Tags resource (create, get, list, update, remove, revert)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="tag",
    collection="tags",
    actions={"create", "get", "list", "update", "remove", "revert"},
    destructive={"remove", "revert"},
)


def gtm_tag(action: str, parent: str | None = None, path: str | None = None,
            config: dict | None = None, confirm: bool = False,
            params: dict | None = None) -> dict:
    """Manage GTM tags within a workspace.

    Actions:
      - list:   parent="accounts/{a}/containers/{c}/workspaces/{w}".
      - get:    path="<workspace>/tags/{tagId}".
      - create: parent=<workspace>, config={tag definition}.
      - update: path="<workspace>/tags/{tagId}", config={...}.
      - remove: path="<workspace>/tags/{tagId}", confirm=true. (destructive)
      - revert: path="<workspace>/tags/{tagId}", confirm=true. (destructive)
    """
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
