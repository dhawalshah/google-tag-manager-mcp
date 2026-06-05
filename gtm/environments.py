"""gtm_environment — Environments (create, get, list, update, remove, reauthorize)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="environment",
    collection="environments",
    actions={"create", "get", "list", "update", "remove", "reauthorize"},
    destructive={"remove", "reauthorize"},
    special={"reauthorize": "POST"},
)


def gtm_environment(action: str, parent: str | None = None, path: str | None = None,
                    config: dict | None = None, confirm: bool = False,
                    params: dict | None = None) -> dict:
    """Manage GTM environments. Standard CRUD (list/create: parent='<container>';
    get/update/remove: path='<container>/environments/{id}') plus:
      - reauthorize: path='<container>/environments/{id}', confirm=true. (destructive)
    """
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
