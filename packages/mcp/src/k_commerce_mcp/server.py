from mcp.server.fastmcp import FastMCP

from k_commerce_mcp.tools.login import login
from k_commerce_mcp.tools.login_status import login_status
from k_commerce_mcp.tools.logout import logout
from k_commerce_mcp.tools.get_providers import get_providers


def create_mcp_server() -> FastMCP:
    mcp_server = FastMCP("k-commerce")
    mcp_server.add_tool(login, name="login", description="Log in to a commerce provider such as Coupang.")
    mcp_server.add_tool(
        login_status,
        name="login_status",
        description="Check login status and whether you are logged in to a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        logout,
        name="logout",
        description="Log out from a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        get_providers,
        name="get_providers",
        description="List supported commerce providers",
    )

    return mcp_server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
