from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import StatusResult
from k_commerce_mcp.tools._result import expect_tool_result


async def status(provider: str) -> StatusResult:
    return expect_tool_result("status", await invoke_tool("status", {"provider": provider}), StatusResult)
