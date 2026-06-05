"""gtm_account — Accounts resource (get, list, update)."""
from gtm import client
from gtm.client import ResourceSpec, dispatch

SPEC = ResourceSpec(
    name="account",
    collection="accounts",
    actions={"get", "list", "update"},
)


def gtm_account(action: str, parent: str | None = None, path: str | None = None,
                config: dict | None = None, params: dict | None = None) -> dict:
    """Manage GTM accounts.

    Actions:
      - list:   list all accessible accounts (no parent needed).
      - get:    get one account. path="accounts/{accountId}".
      - update: update an account. path="accounts/{accountId}", config={...}.
    """
    if action == "list":
        try:
            data = client.request("GET", "accounts", params=params)
            return client.format_response(data, resource="account")
        except client.requests.RequestException as e:
            return client.format_error(str(e), error_code="API_ERROR")
    return dispatch(SPEC, action=action, path=path, config=config, params=params)
