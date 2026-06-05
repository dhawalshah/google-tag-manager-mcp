"""gtm_user_permission — User permissions (create, get, list, update, remove)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="user_permission",
    collection="user_permissions",
    actions={"create", "get", "list", "update", "remove"},
    destructive={"remove"},
)


def gtm_user_permission(action: str, parent: str | None = None, path: str | None = None,
                        config: dict | None = None, confirm: bool = False,
                        params: dict | None = None) -> dict:
    """Manage GTM account user permissions.

    Actions:
      - list:   parent='accounts/{id}'.
      - get:    path='accounts/{id}/user_permissions/{permId}'.
      - create: parent='accounts/{id}', config={emailAddress, accountAccess, containerAccess}.
      - update: path='accounts/{id}/user_permissions/{permId}', config={...}.
      - remove: path='accounts/{id}/user_permissions/{permId}', confirm=true. (destructive)
    """
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
