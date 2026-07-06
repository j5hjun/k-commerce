from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from k_commerce_agent.config import settings

# Registered MCP server connections. Process-local and in-memory, since this
# backend targets a single local demo instance, not multi-tenant/persistent storage.
_servers: dict[str, dict] = {}


def default_server_connection() -> dict:
    """Build the default stdio connection for the bundled k-commerce MCP server."""

    return {
        "transport": "stdio",
        "command": settings.mcp_command,
        "args": list(settings.mcp_args),
    }


def ensure_default_mcp_server() -> None:
    """Register the bundled k-commerce MCP server when it is not already present."""

    name = settings.mcp_server_name
    if name in _servers:
        return
    _servers[name] = default_server_connection()


def list_registered_servers() -> dict[str, dict]:
    return dict(_servers)


def register_servers(servers: dict[str, dict]) -> None:
    """Add (or overwrite by name) registered MCP server connections."""

    _servers.update(servers)


def remove_server(name: str) -> None:
    _servers.pop(name, None)


def build_mcp_client() -> MultiServerMCPClient:
    """Create an MCP client wired to every registered MCP server.

    Tools loaded from this client are stateless: each tool call spawns a fresh
    MCP session (and therefore a fresh CLI subprocess, for stdio servers).
    This is intentional because provider state (cookies/session) is persisted
    to disk by the CLI, so it survives across separate tool invocations.
    """

    return MultiServerMCPClient(list_registered_servers())


async def load_tools() -> list[BaseTool]:
    """Load MCP tools as LangChain tools. Does not require an LLM."""

    client = build_mcp_client()
    return await client.get_tools()
