from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from k_commerce_cli.services.base import Provider
from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.registry import get_provider as default_get_provider, list_providers as default_list_providers
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartQuantityUpdateResult,
    CartQuantityUpdateRequest,
    OrderDetailRequest,
    OrderFailuresRequest,
    OrderListRequest,
    OrderResult,
    OrderSyncRequest,
    ReviewDeleteRequest,
    ReviewDeleteResult,
    ReviewEditRequest,
    ReviewEditResult,
    ReviewUploadRequest,
    ReviewUploadResult,
)

from .registry import get_tool_definition
from .types import JSONValue, ToolInvocationResult, ToolRequestError, ToolRuntimeOptions

ToolPayload = Mapping[str, JSONValue]


async def invoke_tool(
    tool_name: str,
    payload: JSONValue,
    *,
    runtime_options: ToolRuntimeOptions | None = None,
) -> ToolInvocationResult:
    try:
        _ = get_tool_definition(tool_name)
    except KeyError as exc:
        raise ToolRequestError(
            tool_name,
            f"Unknown tool: {tool_name}",
            error_code="unknown_tool",
        ) from exc

    request = _parse_payload(tool_name, payload)
    options = runtime_options or ToolRuntimeOptions()

    match tool_name:
        case "get_providers":
            list_providers = options.list_providers or default_list_providers
            return list_providers()
        case "login":
            return await _get_provider(tool_name, request, options).login()
        case "status":
            return await _get_provider(tool_name, request, options).status()
        case "logout":
            return await _get_provider(tool_name, request, options).logout()
        case "order_sync":
            return await _invoke_order_sync(request, options)
        case "order_list":
            return await _invoke_order_list(request, options)
        case "order_detail":
            return await _invoke_order_detail(request, options)
        case "order_failures":
            return await _invoke_order_failures(request, options)
        case "cart_list":
            return await _get_provider(tool_name, request, options).list_cart()
        case "cart_update_quantity":
            return await _invoke_cart_update_quantity(request, options)
        case "cart_delete_item":
            return await _invoke_cart_delete_item(request, options)
        case "cart_delete_items":
            return await _invoke_cart_delete_items(request, options)
        case "cart_clear":
            return await _get_provider(tool_name, request, options).clear_cart()
        case "search_products":
            return await _invoke_search_products(request, options)
        case "review_list_reviewable":
            return await _get_provider(tool_name, request, options).list_reviewable()
        case "review_list_editable":
            return await _get_provider(tool_name, request, options).list_editable()
        case "review_upload":
            return await _invoke_review_upload(request, options)
        case "review_edit":
            return await _invoke_review_edit(request, options)
        case "review_delete":
            return await _invoke_review_delete(request, options)
        case _:
            raise ToolRequestError(tool_name, f"Tool is registered but not invokable: {tool_name}")


def _parse_payload(tool_name: str, payload: JSONValue) -> ToolPayload:
    if not isinstance(payload, Mapping):
        raise ToolRequestError(tool_name, "Payload must be a JSON object", error_code="invalid_payload")
    if "root_dir" in payload:
        raise ToolRequestError(
            tool_name,
            "root_dir is a runtime option and is not part of the canonical request payload",
            field="root_dir",
            error_code="runtime_option_in_payload",
        )
    return payload


def _get_provider(tool_name: str, payload: ToolPayload, options: ToolRuntimeOptions) -> Provider:
    provider_name = _required_str(tool_name, payload, "provider")
    get_provider = options.get_provider or default_get_provider
    try:
        return get_provider(
            provider_name,
            root_dir=options.root_dir,
            terminal=options.terminal,
        )
    except ValueError as exc:
        raise ToolRequestError(
            tool_name,
            str(exc),
            error_code="unsupported_provider",
            next_tools=("get_providers",),
        ) from exc


async def _invoke_order_sync(payload: ToolPayload, options: ToolRuntimeOptions) -> OrderResult:
    refresh = _optional_bool(payload, "refresh", default=False)
    failed_only = _optional_bool(payload, "failed_only", default=False)
    if refresh and failed_only:
        raise ToolRequestError(
            "order_sync",
            "refresh and failed_only cannot both be true",
            error_code="conflicting_options",
        )
    request = OrderSyncRequest(
        start_date=_optional_date_str("order_sync", payload, "start_date"),
        end_date=_optional_date_str("order_sync", payload, "end_date"),
        failed_only=failed_only,
        refresh=refresh,
    )
    provider = _get_provider("order_sync", payload, options)
    return await provider.sync_orders(request)


async def _invoke_order_list(payload: ToolPayload, options: ToolRuntimeOptions) -> OrderResult:
    _reject_fields("order_list", payload, ("refresh", "failed_only"))
    request = OrderListRequest(
        start_date=_optional_date_str("order_list", payload, "start_date"),
        end_date=_optional_date_str("order_list", payload, "end_date"),
        status=_optional_str(payload, "status", default="all"),
        limit=_optional_limit("order_list", payload, "limit", default=50),
        cursor=_optional_cursor("order_list", payload, "cursor"),
    )
    provider = _get_provider("order_list", payload, options)
    return await provider.list_orders(request)


async def _invoke_order_detail(payload: ToolPayload, options: ToolRuntimeOptions) -> OrderResult:
    request = OrderDetailRequest(order_id=_required_str("order_detail", payload, "order_id"))
    provider = _get_provider("order_detail", payload, options)
    return await provider.get_order_detail(request)


async def _invoke_order_failures(payload: ToolPayload, options: ToolRuntimeOptions) -> OrderResult:
    request = OrderFailuresRequest(
        start_date=_optional_date_str("order_failures", payload, "start_date"),
        end_date=_optional_date_str("order_failures", payload, "end_date"),
        limit=_optional_limit("order_failures", payload, "limit", default=50),
    )
    provider = _get_provider("order_failures", payload, options)
    return await provider.list_order_failures(request)


async def _invoke_cart_update_quantity(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> CartQuantityUpdateResult:
    quantity = _required_int("cart_update_quantity", payload, "quantity")
    if quantity < 1:
        raise ToolRequestError(
            "cart_update_quantity",
            "quantity must be at least 1",
            field="quantity",
            error_code="invalid_field",
        )
    request = CartQuantityUpdateRequest(
        quantity=quantity,
        product_id=_optional_str(payload, "product_id"),
        vendor_item_id=_optional_str(payload, "vendor_item_id"),
        item_id=_optional_str(payload, "item_id"),
    )
    return await _get_provider("cart_update_quantity", payload, options).update_cart_quantity(request)


async def _invoke_cart_delete_item(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> CartDeleteResult:
    request = _cart_delete_request(payload)
    return await _get_provider("cart_delete_item", payload, options).delete_cart_item(request)


async def _invoke_cart_delete_items(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> CartDeleteResult:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ToolRequestError(
            "cart_delete_items",
            "items must be a non-empty list",
            field="items",
            error_code="invalid_field",
        )
    if not items:
        raise ToolRequestError(
            "cart_delete_items",
            "items must be a non-empty list",
            field="items",
            error_code="invalid_field",
        )
    requests = tuple(
        _cart_delete_request_from_value("cart_delete_items", item)
        for item in items
    )
    return await _get_provider("cart_delete_items", payload, options).delete_cart_items(requests)


async def _invoke_search_products(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> SearchProductResult:
    keyword = _required_str("search_products", payload, "keyword")
    category = _optional_nullable_str(payload, "category")
    sort = _optional_str(payload, "sort", default="relevance")
    max_results = _optional_int(payload, "max_results", default=10)
    provider = _get_provider("search_products", payload, options)
    return await provider.search_products(
        keyword,
        category=category,
        sort=sort,
        max_results=max_results,
    )


async def _invoke_review_upload(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> ReviewUploadResult:
    request = ReviewUploadRequest(
        order_id=_required_str("review_upload", payload, "order_id"),
        product_id=_required_str("review_upload", payload, "product_id"),
        rating=_required_int("review_upload", payload, "rating"),
        text=_required_str("review_upload", payload, "text", allow_empty=True),
        review_url=_required_str("review_upload", payload, "review_url"),
    )
    return await _get_provider("review_upload", payload, options).upload_review(request)


async def _invoke_review_edit(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> ReviewEditResult:
    request = ReviewEditRequest(
        order_id=_required_str("review_edit", payload, "order_id"),
        product_id=_required_str("review_edit", payload, "product_id"),
        review_id=_required_str("review_edit", payload, "review_id"),
        rating=_required_int("review_edit", payload, "rating"),
        text=_required_str("review_edit", payload, "text", allow_empty=True),
    )
    return await _get_provider("review_edit", payload, options).edit_review(request)


async def _invoke_review_delete(
    payload: ToolPayload,
    options: ToolRuntimeOptions,
) -> ReviewDeleteResult:
    request = ReviewDeleteRequest(
        review_id=_required_str("review_delete", payload, "review_id"),
        product_id=_optional_str(payload, "product_id"),
        order_id=_optional_str(payload, "order_id"),
    )
    return await _get_provider("review_delete", payload, options).delete_review(request)


def _cart_delete_request(payload: ToolPayload) -> CartDeleteRequest:
    return CartDeleteRequest(
        product_id=_optional_str(payload, "product_id"),
        vendor_item_id=_optional_str(payload, "vendor_item_id"),
        item_id=_optional_str(payload, "item_id"),
    )


def _cart_delete_request_from_value(
    tool_name: str,
    value: JSONValue,
) -> CartDeleteRequest:
    if not isinstance(value, Mapping):
        raise ToolRequestError(tool_name, "items must contain JSON objects", field="items", error_code="invalid_field")
    return _cart_delete_request(value)


def _required_str(
    tool_name: str,
    payload: ToolPayload,
    field: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or (not allow_empty and not value):
        raise ToolRequestError(tool_name, f"{field} must be a non-empty string", field=field, error_code="invalid_field")
    return value


def _optional_str(
    payload: ToolPayload,
    field: str,
    *,
    default: str = "",
) -> str:
    value = payload.get(field, default)
    if isinstance(value, str):
        return value
    raise ToolRequestError("payload", f"{field} must be a string", field=field, error_code="invalid_field")


def _optional_nullable_str(payload: ToolPayload, field: str) -> str | None:
    value = payload.get(field)
    if value is None or isinstance(value, str):
        return value
    raise ToolRequestError("payload", f"{field} must be a string or null", field=field, error_code="invalid_field")


def _required_int(tool_name: str, payload: ToolPayload, field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolRequestError(tool_name, f"{field} must be an integer", field=field, error_code="invalid_field")
    return value


def _optional_int(payload: ToolPayload, field: str, *, default: int) -> int:
    value = payload.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolRequestError("payload", f"{field} must be an integer", field=field, error_code="invalid_field")
    return value


def _optional_bool(payload: ToolPayload, field: str, *, default: bool) -> bool:
    value = payload.get(field, default)
    if isinstance(value, bool):
        return value
    raise ToolRequestError("payload", f"{field} must be a boolean", field=field, error_code="invalid_field")


def _optional_date_str(tool_name: str, payload: ToolPayload, field: str) -> str | None:
    value = _optional_nullable_str(payload, field)
    if value is None:
        return None
    try:
        _ = date.fromisoformat(value)
    except ValueError as exc:
        raise ToolRequestError(tool_name, f"{field} must be an ISO date string", field=field, error_code="invalid_period") from exc
    return value


def _optional_limit(tool_name: str, payload: ToolPayload, field: str, *, default: int) -> int:
    value = _optional_int(payload, field, default=default)
    if 1 <= value <= 100:
        return value
    raise ToolRequestError(tool_name, f"{field} must be between 1 and 100", field=field, error_code="invalid_field")


def _optional_cursor(tool_name: str, payload: ToolPayload, field: str) -> str | None:
    value = _optional_nullable_str(payload, field)
    if value is None:
        return None
    if value.isdecimal():
        return value
    raise ToolRequestError(tool_name, f"{field} must be a numeric string or null", field=field, error_code="invalid_field")


def _reject_fields(tool_name: str, payload: ToolPayload, fields: tuple[str, ...]) -> None:
    for field in fields:
        if field in payload:
            raise ToolRequestError(
                tool_name,
                f"{field} belongs to order_sync, not order_list",
                field=field,
                error_code="invalid_field",
                next_tools=("order_sync",),
            )
