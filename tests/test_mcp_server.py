import unittest
from unittest.mock import patch

from k_commerce_mcp import server


class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_mcp_server_registers_login_tool(self) -> None:
        mcp_server = server.create_mcp_server()

        tools = await mcp_server.list_tools()
        tool_names = {tool.name for tool in tools}

        self.assertIn("login", tool_names)

    async def test_login_tool_has_clear_description(self) -> None:
        mcp_server = server.create_mcp_server()

        tools = await mcp_server.list_tools()
        login_tool = next(tool for tool in tools if tool.name == "login")

        self.assertIn("Coupang", login_tool.description)

    def test_login_tool_dispatches_to_login_coupang_for_coupang_provider(self) -> None:
        result = server.login(provider="coupang")

        self.assertEqual(result, "login_coupang is not implemented yet")


class MainEntrypointTests(unittest.TestCase):
    def test_main_runs_mcp_server_over_stdio(self) -> None:
        with patch("k_commerce_mcp.server.create_mcp_server") as create_mcp_server:
            mcp_server = create_mcp_server.return_value

            server.main()

        create_mcp_server.assert_called_once_with()
        mcp_server.run.assert_called_once_with(transport="stdio")
