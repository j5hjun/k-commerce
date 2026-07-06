from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import await_unless_cancelled
from k_commerce_cli.commands.tool_invocation import CachedProviderFactory
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartItem,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ListCartResult,
)
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import JSONValue, ToolProviderFactory, ToolRuntimeOptions

__all__ = [
    "MSG_NO_CART_ITEMS",
    "MSG_INTERACTIVE_CANCELLED",
    "MSG_QUANTITY_UPDATE_EXITED",
    "MSG_DELETE_EXITED",
    "MSG_LIST_CART",
    "MSG_LIST_BROWSE_EXITED",
    "MSG_EXCLUSIVE_FLAGS",
    "get_provider",
    "invoke_tool",
    "resolve_root_dir",
    "report_unless_list_success",
    "cart_delete_request",
    "fetch_cart_list",
    "cached_provider_factory",
    "invoke_cart_clear",
    "invoke_cart_delete_item",
    "invoke_cart_delete_items",
    "invoke_cart_list",
    "invoke_cart_update_quantity",
]

MSG_NO_CART_ITEMS = "장바구니에 담긴 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "장바구니 작업을 취소했습니다."
MSG_QUANTITY_UPDATE_EXITED = "장바구니 수량 수정을 종료했습니다."
MSG_DELETE_EXITED = "장바구니 삭제를 종료했습니다."
MSG_LIST_CART = "쿠팡 장바구니 목록을 조회합니다..."
MSG_LIST_BROWSE_EXITED = "장바구니 목록 보기를 종료했습니다."
MSG_EXCLUSIVE_FLAGS = "--list, --quantity, --delete는 함께 사용할 수 없습니다."


def resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def report_unless_list_success(terminal: Terminal, result: ListCartResult) -> bool:
    if result.success:
        return True
    terminal.error(result.message)
    return False


def cart_delete_request(item: CartItem) -> CartDeleteRequest:
    return CartDeleteRequest(
        product_id=item.product_id,
        vendor_item_id=item.vendor_item_id,
        item_id=item.item_id,
    )


def cached_provider_factory(root_dir: Path | None) -> CachedProviderFactory:
    return CachedProviderFactory(root_dir=root_dir, provider_factory=get_provider)


def _runtime_options(
    root_dir: Path | None,
    terminal: Terminal | None,
    provider_factory: ToolProviderFactory | None,
) -> ToolRuntimeOptions:
    return ToolRuntimeOptions(
        root_dir=root_dir,
        terminal=terminal,
        get_provider=provider_factory or get_provider,
    )


def _cart_delete_payload(request: CartDeleteRequest) -> dict[str, JSONValue]:
    return {
        "product_id": request.product_id,
        "vendor_item_id": request.vendor_item_id,
        "item_id": request.item_id,
    }


async def invoke_cart_list(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal | None,
    provider_factory: ToolProviderFactory | None = None,
) -> ListCartResult:
    return await invoke_tool(
        "cart_list",
        {"provider": provider},
        runtime_options=_runtime_options(root_dir, terminal, provider_factory),
    )


async def invoke_cart_update_quantity(
    provider: str,
    root_dir: Path | None,
    request: CartQuantityUpdateRequest,
    provider_factory: ToolProviderFactory | None = None,
) -> CartQuantityUpdateResult:
    return await invoke_tool(
        "cart_update_quantity",
        {
            "provider": provider,
            "product_id": request.product_id,
            "vendor_item_id": request.vendor_item_id,
            "item_id": request.item_id,
            "quantity": request.quantity,
        },
        runtime_options=_runtime_options(root_dir, None, provider_factory),
    )


async def invoke_cart_delete_item(
    provider: str,
    root_dir: Path | None,
    request: CartDeleteRequest,
    provider_factory: ToolProviderFactory | None = None,
) -> CartDeleteResult:
    return await invoke_tool(
        "cart_delete_item",
        {"provider": provider, **_cart_delete_payload(request)},
        runtime_options=_runtime_options(root_dir, None, provider_factory),
    )


async def invoke_cart_delete_items(
    provider: str,
    root_dir: Path | None,
    requests: tuple[CartDeleteRequest, ...],
    provider_factory: ToolProviderFactory | None = None,
) -> CartDeleteResult:
    items: list[JSONValue] = [_cart_delete_payload(request) for request in requests]
    payload: dict[str, JSONValue] = {
        "provider": provider,
        "items": items,
    }
    return await invoke_tool(
        "cart_delete_items",
        payload,
        runtime_options=_runtime_options(root_dir, None, provider_factory),
    )


async def invoke_cart_clear(
    provider: str,
    root_dir: Path | None,
    provider_factory: ToolProviderFactory | None = None,
) -> CartDeleteResult:
    return await invoke_tool(
        "cart_clear",
        {"provider": provider},
        runtime_options=_runtime_options(root_dir, None, provider_factory),
    )


async def fetch_cart_list(
    terminal: Terminal,
    provider: str,
    root_dir: Path | None,
    provider_factory: ToolProviderFactory | None = None,
) -> ListCartResult | None:
    terminal.info(MSG_LIST_CART)
    list_result = await await_unless_cancelled(
        terminal,
        invoke_cart_list(provider, root_dir, terminal, provider_factory),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    if not report_unless_list_success(terminal, list_result):
        return None
    if not list_result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return None
    return list_result
