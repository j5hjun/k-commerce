from fastapi import APIRouter, HTTPException
from langchain_mcp_adapters.client import MultiServerMCPClient

from k_commerce_agent.mcp_client import (
    list_registered_servers,
    register_servers,
    remove_server,
)
from k_commerce_agent.schemas import MCPRegisterRequest, MCPServerInfo, MCPServersResponse

router = APIRouter()


@router.get("/api/mcp/servers", response_model=MCPServersResponse)
async def get_servers() -> MCPServersResponse:
    """List every registered MCP server."""

    return await _servers_response()


@router.post("/api/mcp/servers", response_model=MCPServersResponse)
async def register(request: MCPRegisterRequest) -> MCPServersResponse:
    """Register (or overwrite by name) MCP servers from a Cursor-style ``mcp.json`` body.

    Each server is connection-tested before being kept: if any fails to list
    tools, the whole request is rejected so the registry never holds a dead
    entry.
    """

    connections = {name: entry.to_connection() for name, entry in request.mcp_servers.items()}
    probe_client = MultiServerMCPClient({**list_registered_servers(), **connections})

    errors: dict[str, str] = {}
    for name in connections:
        try:
            await probe_client.get_tools(server_name=name)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller, not swallowed
            errors[name] = str(exc)

    if errors:
        raise HTTPException(status_code=400, detail={"failed": errors})

    register_servers(connections)
    return await _servers_response()


@router.delete("/api/mcp/servers/{name}", response_model=MCPServersResponse)
async def delete_server(name: str) -> MCPServersResponse:
    remove_server(name)
    return await _servers_response()


async def _servers_response() -> MCPServersResponse:
    servers = list_registered_servers()
    client = MultiServerMCPClient(servers)

    infos: list[MCPServerInfo] = []
    for name, connection in servers.items():
        try:
            tools = await client.get_tools(server_name=name)
            infos.append(
                MCPServerInfo(
                    name=name,
                    transport=connection["transport"],
                    tools=[tool.name for tool in tools],
                    config=connection,
                )
            )
        except Exception as exc:  # noqa: BLE001 - reported per-server, not raised
            infos.append(
                MCPServerInfo(
                    name=name,
                    transport=connection["transport"],
                    tools=[],
                    config=connection,
                    error=str(exc),
                )
            )

    return MCPServersResponse(servers=infos)
