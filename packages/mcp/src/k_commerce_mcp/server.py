from mcp.server.fastmcp import FastMCP

from k_commerce_cli.services.tools import get_tool_definition
from k_commerce_mcp.tools.cart import (
    cart_clear,
    cart_delete_item,
    cart_delete_items,
    cart_list,
    cart_update_quantity,
)
from k_commerce_mcp.tools.get_providers import get_providers
from k_commerce_mcp.tools.login import login
from k_commerce_mcp.tools.logout import logout
from k_commerce_mcp.tools.order import order_detail, order_failures, order_list, order_search, order_sync
from k_commerce_mcp.tools.product import product_detail
from k_commerce_mcp.tools.review import (
    review_delete,
    review_edit,
    review_list_editable,
    review_list_reviewable,
    review_upload,
)
from k_commerce_mcp.tools.search import search_products
from k_commerce_mcp.tools.status import status


def create_mcp_server() -> FastMCP:
    mcp_server = FastMCP("k-commerce")
    for name, tool in (
        ("get_providers", get_providers),
        ("login", login),
        ("status", status),
        ("logout", logout),
        ("order_sync", order_sync),
        ("order_list", order_list),
        ("order_search", order_search),
        ("order_detail", order_detail),
        ("order_failures", order_failures),
        ("product_detail", product_detail),
        ("cart_list", cart_list),
        ("cart_update_quantity", cart_update_quantity),
        ("cart_delete_item", cart_delete_item),
        ("cart_delete_items", cart_delete_items),
        ("cart_clear", cart_clear),
        ("search_products", search_products),
        ("review_list_reviewable", review_list_reviewable),
        ("review_list_editable", review_list_editable),
        ("review_upload", review_upload),
        ("review_edit", review_edit),
        ("review_delete", review_delete),
    ):
        mcp_server.add_tool(
            tool,
            name=name,
            description=get_tool_definition(name).description,
        )

    return mcp_server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
