"""gtm_folder — Folders (create, get, list, update, remove, revert, entities, move_entities_to_folder)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="folder",
    collection="folders",
    actions={"create", "get", "list", "update", "remove", "revert",
             "entities", "move_entities_to_folder"},
    destructive={"remove", "revert", "move_entities_to_folder"},
    special={"entities": "GET", "move_entities_to_folder": "PUT"},
)


def gtm_folder(action: str, parent: str | None = None, path: str | None = None,
               config: dict | None = None, confirm: bool = False,
               params: dict | None = None) -> dict:
    """Manage GTM folders.

    Standard CRUD+revert like gtm_tag, plus:
      - entities:                 path="<workspace>/folders/{id}" → list entities in folder. (read-only)
      - move_entities_to_folder:  path="<workspace>/folders/{id}", params={tagId/triggerId/variableId},
                                  confirm=true. Moves entities into the folder. (destructive)
    """
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
