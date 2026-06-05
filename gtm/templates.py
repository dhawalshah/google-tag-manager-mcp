"""gtm_template — Templates (create, get, list, update, remove, revert, import_from_gallery)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="template",
    collection="templates",
    actions={"create", "get", "list", "update", "remove", "revert", "import_from_gallery"},
    destructive={"remove", "revert", "import_from_gallery"},
    special={"import_from_gallery": "POST"},
)


def gtm_template(action: str, parent: str | None = None, path: str | None = None,
                 config: dict | None = None, confirm: bool = False,
                 params: dict | None = None) -> dict:
    """Manage GTM custom templates. Standard CRUD+revert plus:
      - import_from_gallery: parent=<workspace> (or path="<workspace>/templates"),
                             confirm=true. Imports a Community Template Gallery template.
    """
    if action == "import_from_gallery" and parent and not path:
        path = f"{parent}/templates"
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
