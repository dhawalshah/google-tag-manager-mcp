"""gtm_gtag_config — Google tag config (create, get, list, update, remove)."""
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="gtag_config",
    collection="gtag_config",
    actions={"create", "get", "list", "update", "remove"},
    destructive={"remove"},
)


def gtm_gtag_config(action: str, parent: str | None = None, path: str | None = None,
                    config: dict | None = None, confirm: bool = False,
                    params: dict | None = None) -> dict:
    """Manage GTM Google tag (gtag) config. Standard CRUD (no revert)."""
    return dispatch(SPEC, action=action, parent=parent, path=path,
                    config=config, confirm=confirm, params=params)
