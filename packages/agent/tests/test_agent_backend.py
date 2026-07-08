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


def test_ensure_default_mcp_server_registers_k_commerce_once() -> None:
    from k_commerce_agent import mcp_client

    mcp_client._servers.clear()
    try:
        mcp_client.ensure_default_mcp_server()
        first = mcp_client.list_registered_servers()
        assert "k-commerce" in first
        assert first["k-commerce"]["transport"] == "stdio"
        assert first["k-commerce"]["command"]

        mcp_client.register_servers({"other": {"transport": "stdio", "command": "echo", "args": []}})
        mcp_client.ensure_default_mcp_server()
        second = mcp_client.list_registered_servers()
        assert "k-commerce" in second
        assert "other" in second
        assert second["k-commerce"] == first["k-commerce"]
    finally:
        mcp_client._servers.clear()


def test_with_safe_tool_errors_preserves_content_and_artifact() -> None:
    from langchain_core.tools import StructuredTool

    from k_commerce_agent.agent import _with_safe_tool_errors

    async def failing(**kwargs: object) -> tuple[str, None]:
        raise RuntimeError("boom")

    tool = StructuredTool.from_function(
        coroutine=failing,
        name="status",
        description="test",
        response_format="content_and_artifact",
    )
    wrapped = _with_safe_tool_errors(tool)

    async def invoke_wrapped() -> str:
        return await wrapped.ainvoke({})

    result = asyncio.run(invoke_wrapped())
    assert "boom" in result
    assert "tool_error" in result


def test_with_compact_tool_results_shrinks_order_list() -> None:
    import json

    from langchain_core.tools import StructuredTool

    from k_commerce_agent.agent import _with_compact_tool_results

    orders = [
        {"orderId": index, "title": f"주문{index}", "deliveryGroupList": []}
        for index in range(1, 21)
    ]
    huge = json.dumps(
        {"payload": {"meta": {"summary": {"totalOrders": 20}}, "orders": orders}},
        ensure_ascii=False,
    )

    async def order_list(**kwargs: object) -> tuple[list[dict[str, str]], None]:
        return [{"type": "text", "text": huge}], None

    tool = StructuredTool.from_function(
        coroutine=order_list,
        name="order_list",
        description="test",
        response_format="content_and_artifact",
    )
    wrapped = _with_compact_tool_results(tool)

    async def invoke_wrapped() -> str:
        result = await wrapped.ainvoke({})
        if isinstance(result, tuple):
            content, _artifact = result
        else:
            content = result
        if isinstance(content, list):
            return content[0]["text"]
        return str(content)

    compact = json.loads(asyncio.run(invoke_wrapped()))
    assert compact["total_count"] == 20
    assert compact["shown_count"] == 10
    assert len(compact["items"]) == 10


def test_tool_result_payload_includes_tool_response_content() -> None:
    # Given: a tool result whose content is JSON text.
    from k_commerce_agent.routes.chat import _tool_result_payload

    content = '{"ok":true,"items":[{"name":"item"}]}'

    # When: the websocket payload is built.
    payload = _tool_result_payload("search_products", content, "call_1")

    # Then: the browser receives both completion metadata and the result body.
    assert payload == {
        "type": "tool_result",
        "id": "call_1",
        "name": "search_products",
        "status": "completed",
        "content": content,
    }


def test_tool_result_payload_marks_error_and_includes_message() -> None:
    # Given: a structured tool error payload.
    from k_commerce_agent.routes.chat import _tool_result_payload

    content = '{"error":{"type":"tool_error","message":"boom","tool_name":"status"}}'

    # When: the websocket payload is built.
    payload = _tool_result_payload("status", content, "call_2")

    # Then: the UI sees failure state and can render the error detail collapsed.
    assert payload == {
        "type": "tool_result",
        "id": "call_2",
        "name": "status",
        "status": "failed",
        "content": content,
    }


def test_tool_result_payload_includes_plain_text_response() -> None:
    # Given: a plain-text tool result.
    from k_commerce_agent.routes.chat import _tool_result_payload

    content = "plain result"

    # When: the websocket payload is built.
    payload = _tool_result_payload("web_search", content, None)

    # Then: plain text is sent to the browser.
    assert payload == {
        "type": "tool_result",
        "name": "web_search",
        "status": "completed",
        "content": content,
    }


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
