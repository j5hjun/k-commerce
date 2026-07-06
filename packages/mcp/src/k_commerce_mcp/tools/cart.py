from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartQuantityUpdateResult,
    ListCartResult,
)
from k_commerce_mcp.tools._result import expect_tool_result


async def cart_list(provider: str) -> ListCartResult:
    return expect_tool_result("cart_list", await invoke_tool("cart_list", {"provider": provider}), ListCartResult)


async def cart_update_quantity(
    provider: str,
    quantity: int,
    product_id: str = "",
    vendor_item_id: str = "",
    item_id: str = "",
) -> CartQuantityUpdateResult:
    return expect_tool_result(
        "cart_update_quantity",
        await invoke_tool(
            "cart_update_quantity",
            {
                "provider": provider,
                "quantity": quantity,
                "product_id": product_id,
                "vendor_item_id": vendor_item_id,
                "item_id": item_id,
            },
        ),
        CartQuantityUpdateResult,
    )


async def cart_delete_item(
    provider: str,
    product_id: str = "",
    vendor_item_id: str = "",
    item_id: str = "",
) -> CartDeleteResult:
    return expect_tool_result(
        "cart_delete_item",
        await invoke_tool(
            "cart_delete_item",
            {
                "provider": provider,
                "product_id": product_id,
                "vendor_item_id": vendor_item_id,
                "item_id": item_id,
            },
        ),
        CartDeleteResult,
    )


async def cart_delete_items(
    provider: str,
    items: list[CartDeleteRequest],
) -> CartDeleteResult:
    return expect_tool_result(
        "cart_delete_items",
        await invoke_tool(
            "cart_delete_items",
            {
                "provider": provider,
                "items": [
                    {
                        "product_id": item.product_id,
                        "vendor_item_id": item.vendor_item_id,
                        "item_id": item.item_id,
                    }
                    for item in items
                ],
            },
        ),
        CartDeleteResult,
    )


async def cart_clear(provider: str) -> CartDeleteResult:
    return expect_tool_result("cart_clear", await invoke_tool("cart_clear", {"provider": provider}), CartDeleteResult)
