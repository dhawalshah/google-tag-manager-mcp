"""gtm_container — Containers (create, get, list, update, remove, combine, lookup, move_tag_id, snippet)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="container",
    collection="containers",
    actions={"create", "get", "list", "update", "remove",
             "combine", "lookup", "move_tag_id", "snippet"},
    destructive={"remove", "combine", "move_tag_id"},
    special={"combine": "POST", "lookup": "GET", "move_tag_id": "POST", "snippet": "GET"},
)


def gtm_container(action: str, parent: str | None = None, path: str | None = None,
                  config: dict | None = None, confirm: bool = False,
                  params: dict | None = None) -> dict:
    """Manage GTM containers.

    Standard CRUD (list/create: parent='accounts/{a}'; get/update/remove: path='accounts/{a}/containers/{c}') plus:
      - combine:     path=<container>, params={containerId,...}, confirm=true. (destructive)
      - lookup:      params={destinationId} -> find container by destination. (read-only; no parent/path needed)
      - move_tag_id: path=<container>, params={...}, confirm=true. (destructive)
      - snippet:     path=<container> -> GTM install snippet. (read-only)
    """
    if action == "lookup":
        # Root-level lookup: GET accounts/containers:lookup
        path = "accounts/containers"
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
