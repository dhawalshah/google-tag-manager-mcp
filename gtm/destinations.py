"""gtm_destination — Destinations (get, list, link)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="destination",
    collection="destinations",
    actions={"get", "list", "link"},
    destructive={"link"},
    special={"link": "POST"},
)


def gtm_destination(action: str, parent: str | None = None, path: str | None = None,
                    config: dict | None = None, confirm: bool = False,
                    params: dict | None = None) -> dict:
    """Manage GTM destinations.

    Actions:
      - list:   parent='<container>'.
      - get:    path='<container>/destinations/{id}'.
      - link:   parent='<container>', params={destinationId}, confirm=true.
                (Note: Google has deprecated destination linking via API.) (destructive)
    """
    if action == "link" and parent and not path:
        path = f"{parent}/destinations"
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
