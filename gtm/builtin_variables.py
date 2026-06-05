"""gtm_built_in_variable — Built-in Variables (create, list, remove, revert)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="built_in_variable",
    collection="built_in_variables",
    actions={"create", "list", "remove", "revert"},
    destructive={"remove", "revert"},
)


def gtm_built_in_variable(action: str, parent: str | None = None, path: str | None = None,
                          confirm: bool = False, params: dict | None = None,
                          config: dict | None = None) -> dict:
    """Manage GTM built-in variables.

    Actions:
      - list:   parent=<workspace>.
      - create: parent=<workspace>, params={"type": "<builtInType>"}.
      - remove: path="<workspace>/built_in_variables", params={"type": "..."}, confirm=true.
      - revert: path="<workspace>/built_in_variables", params={"type": "..."}, confirm=true.
    """
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
