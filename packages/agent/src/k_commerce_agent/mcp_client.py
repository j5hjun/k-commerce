from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from k_commerce_agent.config import settings


def build_mcp_client() -> MultiServerMCPClient:
    """Create an MCP client wired to the K-commerce MCP server over stdio.

    Tools loaded from this client are stateless: each tool call spawns a fresh
    MCP session (and therefore a fresh CLI subprocess). This is intentional
    because provider state (cookies/session) is persisted to disk by the CLI,
    so it survives across separate tool invocations.
    """

    return MultiServerMCPClient(
        {
            settings.mcp_server_name: {
                "transport": "stdio",
                "command": settings.mcp_command,
                "args": settings.mcp_args,
            }
        }
    )


async def load_tools() -> list[BaseTool]:
    """Load MCP tools as LangChain tools. Does not require an LLM."""

    client = build_mcp_client()
    return await client.get_tools()
