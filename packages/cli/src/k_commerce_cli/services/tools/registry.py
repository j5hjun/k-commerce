from __future__ import annotations

from typing import Final

from .types import ToolDefinition

_TOOL_DEFINITIONS: Final[tuple[ToolDefinition, ...]] = (
    ToolDefinition("get_providers", "List supported commerce providers."),
    ToolDefinition("login", "Log in to a commerce provider."),
    ToolDefinition("status", "Check provider login status."),
    ToolDefinition("logout", "Log out from a commerce provider."),
    ToolDefinition("order_sync", "Collect provider orders into the local order snapshot."),
    ToolDefinition("order_list", "List saved provider orders without opening a browser."),
    ToolDefinition("order_detail", "Show one saved provider order in detail."),
    ToolDefinition("order_failures", "List saved provider orders that need attention."),
    ToolDefinition("cart_list", "List cart items."),
    ToolDefinition("cart_update_quantity", "Update a cart item quantity."),
    ToolDefinition("cart_delete_item", "Delete one cart item."),
    ToolDefinition("cart_delete_items", "Delete multiple cart items."),
    ToolDefinition("cart_clear", "Clear the provider cart."),
    ToolDefinition("search_products", "Search provider products."),
    ToolDefinition("review_list_reviewable", "List products eligible for review."),
    ToolDefinition("review_list_editable", "List editable reviews."),
    ToolDefinition("review_upload", "Upload a product review."),
    ToolDefinition("review_edit", "Edit a product review."),
    ToolDefinition("review_delete", "Delete a product review."),
)

_TOOL_DEFINITION_BY_NAME: Final[dict[str, ToolDefinition]] = {
    definition.name: definition for definition in _TOOL_DEFINITIONS
}


def list_tool_names() -> list[str]:
    return [definition.name for definition in _TOOL_DEFINITIONS]


def get_tool_definition(name: str) -> ToolDefinition:
    return _TOOL_DEFINITION_BY_NAME[name]
