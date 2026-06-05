"""gtm_client — Clients resource (create, get, list, update, remove, revert)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="client",
    collection="clients",
    actions={"create", "get", "list", "update", "remove", "revert"},
    destructive={"remove", "revert"},
)


def gtm_client(action: str, parent: str | None = None, path: str | None = None,
               config: dict | None = None, confirm: bool = False,
               params: dict | None = None) -> dict:
    """Manage GTM clients within a workspace. Same action set as gtm_tag
    (create, get, list, update, remove, revert; remove/revert require confirm=true)."""
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
