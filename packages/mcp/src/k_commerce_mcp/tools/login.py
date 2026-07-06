from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import LoginResult
from k_commerce_mcp.tools._result import expect_tool_result


async def login(provider: str) -> LoginResult:
    return expect_tool_result("login", await invoke_tool("login", {"provider": provider}), LoginResult)
