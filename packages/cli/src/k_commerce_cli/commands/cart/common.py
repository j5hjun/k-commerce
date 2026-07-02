from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import await_unless_cancelled
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import CartDeleteRequest, CartItem, ListCartResult

__all__ = [
    "MSG_NO_CART_ITEMS",
    "MSG_INTERACTIVE_CANCELLED",
    "MSG_QUANTITY_UPDATE_EXITED",
    "MSG_DELETE_EXITED",
    "MSG_LIST_CART",
    "MSG_LIST_BROWSE_EXITED",
    "MSG_EXCLUSIVE_FLAGS",
    "get_provider",
    "resolve_root_dir",
    "report_unless_list_success",
    "cart_delete_request",
    "fetch_cart_list",
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


async def fetch_cart_list(terminal: Terminal, list_provider) -> ListCartResult | None:
    terminal.info(MSG_LIST_CART)
    list_result = await await_unless_cancelled(
        terminal,
        list_provider.list_cart(),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    if not report_unless_list_success(terminal, list_result):
        return None
    if not list_result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return None
    return list_result
