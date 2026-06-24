from mcp.server.fastmcp import FastMCP

from k_commerce_mcp.tools.login import login


def create_mcp_server() -> FastMCP:
    mcp_server = FastMCP("k-commerce")
    mcp_server.add_tool(login, name="login", description="Log in to a commerce provider such as Coupang.")
    return mcp_server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
