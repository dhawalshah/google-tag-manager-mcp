"""Tests that all 18 GTM tools are registered in server.py."""
import asyncio
import server


def _tool_names() -> set[str]:
    """Return the set of registered tool names via FastMCP list_tools()."""
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name for t in tools}


def test_all_18_tools_registered():
    names = _tool_names()
    expected = {
        "gtm_account", "gtm_container", "gtm_workspace", "gtm_tag", "gtm_trigger",
        "gtm_variable", "gtm_built_in_variable", "gtm_folder", "gtm_client",
        "gtm_zone", "gtm_template", "gtm_transformation", "gtm_gtag_config",
        "gtm_destination", "gtm_environment", "gtm_version", "gtm_version_header",
        "gtm_user_permission",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"
    extra = names - expected
    assert not extra, f"unexpected tools registered: {extra}"


def test_exactly_18_gtm_tools():
    names = _tool_names()
    gtm_tools = {n for n in names if n.startswith("gtm_")}
    assert len(gtm_tools) == 18, f"expected 18, got {len(gtm_tools)}: {sorted(gtm_tools)}"
