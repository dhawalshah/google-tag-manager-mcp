"""Google Tag Manager MCP Server — tool registrations."""
from fastmcp import FastMCP
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

mcp = FastMCP("Google Tag Manager Tools")

from gtm.accounts import gtm_account
from gtm.containers import gtm_container
from gtm.workspaces import gtm_workspace
from gtm.tags import gtm_tag
from gtm.triggers import gtm_trigger
from gtm.variables import gtm_variable
from gtm.builtin_variables import gtm_built_in_variable
from gtm.folders import gtm_folder
from gtm.clients import gtm_client
from gtm.zones import gtm_zone
from gtm.templates import gtm_template
from gtm.transformations import gtm_transformation
from gtm.gtag_config import gtm_gtag_config
from gtm.destinations import gtm_destination
from gtm.environments import gtm_environment
from gtm.versions import gtm_version
from gtm.version_headers import gtm_version_header
from gtm.user_permissions import gtm_user_permission

for _tool in (
    gtm_account, gtm_container, gtm_workspace, gtm_tag, gtm_trigger, gtm_variable,
    gtm_built_in_variable, gtm_folder, gtm_client, gtm_zone, gtm_template,
    gtm_transformation, gtm_gtag_config, gtm_destination, gtm_environment,
    gtm_version, gtm_version_header, gtm_user_permission,
):
    mcp.tool(_tool)

if __name__ == "__main__":
    mcp.run()
