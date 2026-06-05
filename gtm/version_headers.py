"""gtm_version_header — Version headers (list, latest)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="version_header",
    collection="version_headers",
    actions={"list", "latest"},
    special={"latest": "GET"},
)


def gtm_version_header(action: str, parent: str | None = None, path: str | None = None,
                       params: dict | None = None) -> dict:
    """List GTM container version headers.

    Actions:
      - list:   parent='<container>'.
      - latest: parent='<container>' -> latest version header. (read-only)
    """
    if action == "latest" and parent and not path:
        path = f"{parent}/version_headers"
    return dispatch(SPEC, action=action, parent=parent, path=path, params=params)
