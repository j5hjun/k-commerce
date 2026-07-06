from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import OrderResult
from k_commerce_mcp.tools._result import expect_tool_result


async def order_list(
    provider: str,
    refresh: bool = False,
    failed_only: bool = False,
) -> OrderResult:
    return expect_tool_result(
        "order_list",
        await invoke_tool(
            "order_list",
            {"provider": provider, "refresh": refresh, "failed_only": failed_only},
        ),
        OrderResult,
    )
