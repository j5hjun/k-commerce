from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.types import LoginResult, StatusResult
from k_commerce_mcp import server


@pytest.mark.anyio
async def test_create_mcp_server_registers_login_and_login_status_tools() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "login" in tool_names
    assert "login_status" in tool_names


@pytest.mark.anyio
async def test_login_tool_has_clear_description() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    login_tool = next(tool for tool in tools if tool.name == "login")

    assert "Coupang" in login_tool.description


@pytest.mark.anyio
async def test_login_status_tool_has_clear_description() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    login_status_tool = next(tool for tool in tools if tool.name == "login_status")

    assert "status" in login_status_tool.description.lower()
    assert "logged in" in login_status_tool.description.lower()


@pytest.mark.anyio
async def test_login_tool_returns_provider_login_result_for_coupang_provider() -> None:
    expected = LoginResult(
        provider="coupang",
        success=True,
        message="쿠팡 로그인 성공",
    )
    mocked_provider = type("MockProvider", (), {"login": AsyncMock(return_value=expected)})()

    with patch("k_commerce_mcp.tools.login.get_provider", return_value=mocked_provider) as get_provider:
        result = await server.login(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.login.assert_awaited_once_with()


@pytest.mark.anyio
async def test_login_status_tool_returns_provider_status_result_for_coupang_provider() -> None:
    expected = StatusResult(
        provider="coupang",
        logged_in=True,
        message="쿠팡 로그인 상태입니다",
    )
    mocked_provider = type("MockProvider", (), {"status": AsyncMock(return_value=expected)})()

    with patch(
        "k_commerce_mcp.tools.login_status.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.login_status(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.status.assert_awaited_once_with()


def test_main_runs_mcp_server_over_stdio() -> None:
    with patch("k_commerce_mcp.server.create_mcp_server") as create_mcp_server:
        mcp_server = create_mcp_server.return_value

        server.main()

    create_mcp_server.assert_called_once_with()
    mcp_server.run.assert_called_once_with(transport="stdio")


@pytest.mark.anyio
async def test_get_providers_tool_is_registered() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "get_providers" in tool_names
