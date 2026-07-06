from mcp.server.fastmcp import FastMCP

from k_commerce_mcp.tools.cart import (
    cart_clear,
    cart_delete_item,
    cart_delete_items,
    cart_list,
    cart_update_quantity,
    cart_update_quantity_smart,
)
from k_commerce_mcp.tools.get_providers import get_providers
from k_commerce_mcp.tools.login import login
from k_commerce_mcp.tools.login_status import login_status
from k_commerce_mcp.tools.logout import logout
from k_commerce_mcp.tools.order import order_delivery_tracking, order_list
from k_commerce_mcp.tools.review import (
    review_delete,
    review_edit,
    review_list,
    review_list_editable,
    review_list_reviewable,
    review_upload,
)
from k_commerce_mcp.tools.search import search_products


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
        order_delivery_tracking,
        name="order_delivery_tracking",
        description=(
            "Open the provider delivery tracking view for a specific shipment and return live tracking details "
            "such as summary, courier name, invoice number, and event lines."
        ),
    )
    mcp_server.add_tool(
        review_list,
        name="review_list",
        description="List reviewable products and editable reviews in one browser session.",
    )
    mcp_server.add_tool(
        review_list_reviewable,
        name="review_list_reviewable",
        description="List products that can still receive a new review for a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        review_list_editable,
        name="review_list_editable",
        description="List reviews that can be edited or deleted for a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        review_upload,
        name="review_upload",
        description="Create a new product review for a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        review_edit,
        name="review_edit",
        description="Edit an existing product review for a commerce provider such as Coupang.",
    )
    mcp_server.add_tool(
        review_delete,
        name="review_delete",
        description="Delete an existing product review for a commerce provider such as Coupang.",
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
        cart_update_quantity_smart,
        name="cart_update_quantity_smart",
        description=(
            "Update cart quantity using the visible cart item index or product name instead of raw IDs. "
            "Use this when the user refers to '1번 상품' or repeats the product name from cart_list."
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
    mcp_server.add_tool(
        search_products,
        name="search_products",
        description=(
            "Search products for a commerce provider such as Coupang. "
            "Use keyword from the user's shopping intent, and low_price sort when the user wants the cheapest option."
        ),
    )

    return mcp_server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
