from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import (
    OrderDetailResult,
    OrderFailuresResult,
    OrderListResult,
    OrderSyncResult,
)
from k_commerce_mcp.tools._result import expect_tool_result


async def order_sync(
    provider: str,
    start_date: str | None = None,
    end_date: str | None = None,
    failed_only: bool = False,
    refresh: bool = False,
) -> OrderSyncResult:
    return expect_tool_result(
        "order_sync",
        await invoke_tool(
            "order_sync",
            {
                "provider": provider,
                "start_date": start_date,
                "end_date": end_date,
                "failed_only": failed_only,
                "refresh": refresh,
            },
        ),
        OrderSyncResult,
    )


async def order_list(
    provider: str,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str = "all",
    limit: int = 50,
    cursor: str | None = None,
) -> OrderListResult:
    return expect_tool_result(
        "order_list",
        await invoke_tool(
            "order_list",
            {
                "provider": provider,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "limit": limit,
                "cursor": cursor,
            },
        ),
        OrderListResult,
    )


async def order_detail(provider: str, order_id: str) -> OrderDetailResult:
    return expect_tool_result(
        "order_detail",
        await invoke_tool(
            "order_detail",
            {"provider": provider, "order_id": order_id},
        ),
        OrderDetailResult,
    )


async def order_failures(
    provider: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> OrderFailuresResult:
    return expect_tool_result(
        "order_failures",
        await invoke_tool(
            "order_failures",
            {"provider": provider, "start_date": start_date, "end_date": end_date, "limit": limit},
        ),
        OrderFailuresResult,
    )
