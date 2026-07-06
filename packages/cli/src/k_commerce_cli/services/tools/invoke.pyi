from __future__ import annotations

from typing import Literal, overload

from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.types import (
    CartDeleteResult,
    CartQuantityUpdateResult,
    ListCartResult,
    ListEditableReviewsResult,
    ListReviewableResult,
    LoginResult,
    LogoutResult,
    OrderResult,
    ReviewDeleteResult,
    ReviewEditResult,
    ReviewUploadResult,
    StatusResult,
)

from .types import JSONValue, ToolInvocationResult, ToolRuntimeOptions


@overload
async def invoke_tool(tool_name: Literal["get_providers"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> list[str]: ...


@overload
async def invoke_tool(tool_name: Literal["login"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> LoginResult: ...


@overload
async def invoke_tool(tool_name: Literal["status"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> StatusResult: ...


@overload
async def invoke_tool(tool_name: Literal["logout"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> LogoutResult: ...


@overload
async def invoke_tool(tool_name: Literal["order_list"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> OrderResult: ...


@overload
async def invoke_tool(tool_name: Literal["cart_list"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ListCartResult: ...


@overload
async def invoke_tool(tool_name: Literal["cart_update_quantity"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> CartQuantityUpdateResult: ...


@overload
async def invoke_tool(tool_name: Literal["cart_delete_item", "cart_delete_items", "cart_clear"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> CartDeleteResult: ...


@overload
async def invoke_tool(tool_name: Literal["search_products"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> SearchProductResult: ...


@overload
async def invoke_tool(tool_name: Literal["review_list_reviewable"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ListReviewableResult: ...


@overload
async def invoke_tool(tool_name: Literal["review_list_editable"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ListEditableReviewsResult: ...


@overload
async def invoke_tool(tool_name: Literal["review_upload"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ReviewUploadResult: ...


@overload
async def invoke_tool(tool_name: Literal["review_edit"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ReviewEditResult: ...


@overload
async def invoke_tool(tool_name: Literal["review_delete"], payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ReviewDeleteResult: ...


@overload
async def invoke_tool(tool_name: str, payload: JSONValue, *, runtime_options: ToolRuntimeOptions | None = None) -> ToolInvocationResult: ...
