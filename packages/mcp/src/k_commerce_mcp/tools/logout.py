from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import LogoutResult
from k_commerce_mcp.tools._result import expect_tool_result


async def logout(provider: str) -> LogoutResult:
    return expect_tool_result("logout", await invoke_tool("logout", {"provider": provider}), LogoutResult)
