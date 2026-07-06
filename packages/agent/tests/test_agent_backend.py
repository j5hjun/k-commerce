import asyncio

import httpx
import pytest
from mcp.types import Tool

from k_commerce_agent.agent import ModelNotConfiguredError, build_agent
from k_commerce_agent.config import Settings
from k_commerce_agent.main import create_app
from k_commerce_agent.schemas import ToolsResponse
from k_commerce_mcp.server import create_mcp_server


def test_settings_default_mcp_launch_targets_mcp_module() -> None:
    settings = Settings()
    assert settings.mcp_args == ["-m", "k_commerce_mcp.server"]
    assert settings.mcp_server_name == "k-commerce"


def test_build_agent_without_model_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def build_agent_without_model() -> None:
        assert await build_agent() is not None

    monkeypatch.setattr("k_commerce_agent.agent.settings.llm_model", "")
    with pytest.raises(ModelNotConfiguredError):
        asyncio.run(build_agent_without_model())


def test_api_tools_exposes_canonical_mcp_tool_names(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: the MCP client boundary returns the current canonical MCP tools.
    from k_commerce_agent.routes import chat as chat_routes

    canonical_tools = asyncio.run(create_mcp_server().list_tools())
    canonical_names = {tool.name for tool in canonical_tools}
    assert "login_status" not in canonical_names

    async def load_canonical_tools() -> list[Tool]:
        return canonical_tools

    monkeypatch.setattr(chat_routes, "load_tools", load_canonical_tools)

    # When: the agent consumer route lists tools without an LLM.
    async def request_tools_response() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/tools")

    response = asyncio.run(request_tools_response())

    # Then: canonical names are exposed and the removed compatibility name is absent.
    assert response.status_code == 200
    body = ToolsResponse.model_validate_json(response.content)
    names = {tool.name for tool in body.tools}
    assert names == canonical_names
    assert "login_status" not in names
