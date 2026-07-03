from mcp.server.fastmcp import FastMCP

from k_commerce_mcp.tools.cart import (
    cart_clear,
    cart_delete_item,
    cart_delete_items,
    cart_list,
    cart_update_quantity,
)
from k_commerce_mcp.tools.get_providers import get_providers
from k_commerce_mcp.tools.login import login
from k_commerce_mcp.tools.login_status import login_status
from k_commerce_mcp.tools.logout import logout
from k_commerce_mcp.tools.order import order_list


def create_mcp_server() -> FastMCP:
    mcp_server = FastMCP("k-commerce")
    mcp_server.add_tool(
        login,
        name="login",
        description="Log in to a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        login_status,
        name="login_status",
        description="Check login status and whether you are logged in to a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        logout,
        name="logout",
        description="Log out from a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        get_providers,
        name="get_providers",
        description="List supported commerce providers",
    )
    mcp_server.add_tool(
        order_list,
        name="order_list",
        description=(
            "Collect and return the order snapshot for a commerce provider such as Coupang. "
            "Use refresh=true to rebuild the snapshot, or failed_only=true to retry previously failed pages."
        ),
    )
    mcp_server.add_tool(
        cart_list,
        name="cart_list",
        description="List items in the shopping cart for a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        cart_update_quantity,
        name="cart_update_quantity",
        description=(
            "Update the quantity of a cart item for a commerce provider such as Coupang. "
            "Identify the item with product_id, vendor_item_id, and item_id from cart_list."
        ),
    )
    mcp_server.add_tool(
        cart_delete_item,
        name="cart_delete_item",
        description=(
            "Delete a single cart item for a commerce provider such as Coupang. "
            "Identify the item with product_id, vendor_item_id, and item_id from cart_list."
        ),
    )
    mcp_server.add_tool(
        cart_delete_items,
        name="cart_delete_items",
        description=(
            "Delete multiple cart items in one session for a commerce provider such as Coupang. "
            "Pass a list of CartDeleteRequest objects from cart_list item identifiers."
        ),
    )
    mcp_server.add_tool(
        cart_clear,
        name="cart_clear",
        description="Remove all items from the shopping cart for a commerce provider such as Coupang.",
    )

    return mcp_server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
