from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MCPConnection = dict[str, str | list[str] | dict[str, str]]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Incoming websocket payload for a single chat turn.

    Either send a single ``message`` string, or the full ``messages`` history.
    """

    message: str | None = None
    messages: list[ChatMessage] | None = None

    def to_lc_messages(self) -> list[dict[str, str]]:
        if self.messages:
            return [{"role": m.role, "content": m.content} for m in self.messages]
        if self.message:
            return [{"role": "user", "content": self.message}]
        return []


class ToolInfo(BaseModel):
    name: str
    description: str


class ToolsResponse(BaseModel):
    model_configured: bool
    tools: list[ToolInfo]


class MCPServerEntry(BaseModel):
    """One entry of a Cursor-style ``mcpServers`` JSON block.

    Either ``command`` (stdio, spawns a local process) or ``url``
    (remote HTTP/SSE server) must be provided.
    """

    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    transport: Literal["stdio", "sse", "streamable_http", "http"] | None = None

    def to_connection(self) -> MCPConnection:
        if self.command:
            connection: MCPConnection = {
                "transport": "stdio",
                "command": self.command,
                "args": self.args,
            }
            if self.env:
                connection["env"] = self.env
            return connection

        if self.url:
            transport = self.transport or "streamable_http"
            if transport == "http":
                transport = "streamable_http"
            connection = {"transport": transport, "url": self.url}
            if self.headers:
                connection["headers"] = self.headers
            return connection

        raise ValueError("각 MCP 서버 설정에는 'command' 또는 'url' 중 하나가 필요합니다.")


class MCPRegisterRequest(BaseModel):
    """Body for ``POST /api/mcp/servers``, shaped like Cursor's ``mcp.json``."""

    model_config = ConfigDict(populate_by_name=True)

    mcp_servers: dict[str, MCPServerEntry] = Field(alias="mcpServers")


class MCPServerInfo(BaseModel):
    name: str
    transport: str
    tools: list[str]
    config: MCPConnection
    error: str | None = None


class MCPServersResponse(BaseModel):
    servers: list[MCPServerInfo]
