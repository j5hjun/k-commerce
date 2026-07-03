from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Literal, TypeVar

import asyncclick as click
from questionary import Choice

from k_commerce_cli.base import Terminal
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.providers.coupang.cart.utils import format_cart_list
from k_commerce_cli.services.types import CartItem

T = TypeVar("T")

ListDetailAction = Literal["back", "exit"]
CartDeleteMode = Literal["single", "selected", "all", "exit"]
ClearCartAction = Literal["list", "clear", "back", "exit"]
CartItemsSelection = tuple[CartItem, ...] | Literal["back", "exit"]
CartItemSelection = CartItem | Literal["back", "exit"] | None
BulkDeleteConfirmAction = Literal["confirm", "back", "exit"]

# questionary select가 각 항목 앞에 붙이는 포인터/선택 표시(»○   ) 너비
_QUESTIONARY_SELECT_PREFIX = "     "

PRODUCT_NAME_DISPLAY_WIDTH = 54
OPTION_TEXT_DISPLAY_WIDTH = 16

_EXIT_CART_SELECTION = object()
_CONTINUE_CART_SELECTION = object()
_DELETE_MODE_SINGLE = object()
_DELETE_MODE_SELECTED = object()
_DELETE_MODE_ALL = object()
_DELETE_MODE_EXIT = object()
_CLEAR_CART_CLEAR = object()
_CLEAR_CART_LIST = object()
_CLEAR_CART_BACK = object()
_CLEAR_CART_EXIT = object()
_EMPTY_SELECTION_RETRY = object()
_BULK_DELETE_CONFIRM = object()
_BACK_TO_DELETE_MODE = object()
_BACK_TO_LIST = object()
_EXIT_LIST_BROWSE = object()


async def await_unless_cancelled(
    terminal: Terminal,
    awaitable: Awaitable[T],
    *,
    message: str,
) -> T:
    """브라우저 대기 중 Ctrl+C가 들어오면 traceback 없이 취소 메시지로 종료합니다."""
    try:
        return await awaitable
    except (KeyboardInterrupt, asyncio.CancelledError):
        terminal.echo(message)
        raise click.exceptions.Exit(0) from None


def _cart_selection_prompt(prefix: str, count: int, *, browse: bool = False) -> str:
    enter_hint = "Enter로 상세 보기" if browse else "Enter 선택"
    return f"{prefix} (전체 {count}개, ↑↓ 이동, {enter_hint}, Ctrl+C 취소):"


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if _is_wide(char) else 1
    return width


def _is_wide(char: str) -> bool:
    code = ord(char)
    return (
        0x1100 <= code <= 0x11FF
        or 0x2E80 <= code <= 0xA4CF
        or 0xAC00 <= code <= 0xD7A3
        or 0xF900 <= code <= 0xFAFF
        or 0xFE10 <= code <= 0xFE19
        or 0xFE30 <= code <= 0xFE6F
        or 0xFF00 <= code <= 0xFF60
        or 0xFFE0 <= code <= 0xFFE6
    )


def _truncate_display(text: str, max_width: int) -> str:
    if _display_width(text) <= max_width:
        return text

    suffix = "..."
    target_width = max_width - len(suffix)
    result = []
    width = 0
    for char in text:
        char_width = 2 if _is_wide(char) else 1
        if width + char_width > target_width:
            break
        result.append(char)
        width += char_width
    return f"{''.join(result)}{suffix}"


def _pad_display(text: str, width: int) -> str:
    truncated = _truncate_display(text, width)
    return truncated + " " * max(0, width - _display_width(truncated))


CART_LIST_HEADER = (
    f"{_QUESTIONARY_SELECT_PREFIX}{'No':>3}  "
    f"{_pad_display('상품명', PRODUCT_NAME_DISPLAY_WIDTH)}  "
    f"{_pad_display('옵션', OPTION_TEXT_DISPLAY_WIDTH)}  "
    f"{'수량':>4}  {'가격':>12}"
)


def _cart_list_choice_label(item: CartItem) -> str:
    return (
        f"{item.index:>3}  "
        f"{_pad_display(item.product_name, PRODUCT_NAME_DISPLAY_WIDTH)}  "
        f"{_pad_display(item.option_text or '-', OPTION_TEXT_DISPLAY_WIDTH)}  "
        f"{item.quantity:>4}  "
        f"{item.total_price or item.unit_price or '-':>12}"
    )


def _cart_list_choices(items: tuple[CartItem, ...]) -> list[Choice]:
    return [Choice(_cart_list_choice_label(item), value=item) for item in items]


async def prompt_cart_item(
    prompts: Prompts,
    items: tuple[CartItem, ...],
    *,
    selection_prefix: str = "상품을 선택하세요",
    browse: bool = False,
    allow_back: bool = False,
) -> CartItemSelection:
    choices = _cart_list_choices(items)
    if allow_back:
        choices.append(Choice("뒤로가기", value=_BACK_TO_DELETE_MODE))
    choices.append(Choice("나가기", value=_EXIT_CART_SELECTION))

    selected = await prompts.select(
        f"{_cart_selection_prompt(selection_prefix, len(items), browse=browse)}\n"
        f"{CART_LIST_HEADER}",
        choices=choices,
    )
    if selected is _BACK_TO_DELETE_MODE:
        return "back"
    if selected is _EXIT_CART_SELECTION or selected == "나가기":
        return "exit" if allow_back else None
    return selected


async def prompt_cart_continue(
    prompts: Prompts,
    *,
    message: str,
) -> bool:
    selected = await prompts.select(
        message,
        choices=[
            Choice("다른 상품 선택", value=_CONTINUE_CART_SELECTION),
            Choice("나가기", value=_EXIT_CART_SELECTION),
        ],
    )
    return selected is _CONTINUE_CART_SELECTION


async def prompt_delete_mode(prompts: Prompts) -> CartDeleteMode:
    selected = await prompts.select(
        "삭제 방식을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("상품 하나 삭제", value=_DELETE_MODE_SINGLE),
            Choice("여러 상품 삭제", value=_DELETE_MODE_SELECTED),
            Choice("장바구니 비우기", value=_DELETE_MODE_ALL),
            Choice("나가기", value=_DELETE_MODE_EXIT),
        ],
    )
    if selected is _DELETE_MODE_SINGLE:
        return "single"
    if selected is _DELETE_MODE_SELECTED:
        return "selected"
    if selected is _DELETE_MODE_ALL:
        return "all"
    return "exit"


async def prompt_cart_items_empty_action(
    prompts: Prompts,
) -> Literal["retry", "back", "exit"]:
    selected = await prompts.select(
        "삭제할 상품이 선택되지 않았습니다. 다음 작업을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("다시 선택", value=_EMPTY_SELECTION_RETRY),
            Choice("뒤로가기", value=_BACK_TO_DELETE_MODE),
            Choice("나가기", value=_EXIT_CART_SELECTION),
        ],
    )
    if selected is _BACK_TO_DELETE_MODE:
        return "back"
    if selected is _EXIT_CART_SELECTION:
        return "exit"
    return "retry"


def format_selected_cart_delete_list(items: tuple[CartItem, ...]) -> str:
    return format_cart_list(items).replace("장바구니 상품", "삭제할 상품", 1)


async def prompt_bulk_delete_confirmation(prompts: Prompts) -> BulkDeleteConfirmAction:
    selected = await prompts.select(
        "정말 삭제하시겠습니까? (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("삭제", value=_BULK_DELETE_CONFIRM),
            Choice("뒤로가기", value=_BACK_TO_DELETE_MODE),
            Choice("나가기", value=_EXIT_CART_SELECTION),
        ],
    )
    if selected is _BULK_DELETE_CONFIRM:
        return "confirm"
    if selected is _BACK_TO_DELETE_MODE:
        return "back"
    return "exit"


async def prompt_cart_items(
    prompts: Prompts,
    items: tuple[CartItem, ...],
    *,
    selection_prefix: str = "삭제할 상품을 선택하세요",
) -> CartItemsSelection:
    choices = _cart_list_choices(items)
    choices.append(Choice("뒤로가기", value=_BACK_TO_DELETE_MODE))
    choices.append(Choice("나가기", value=_EXIT_CART_SELECTION))

    while True:
        selected = await prompts.checkbox(
            f"{selection_prefix} (전체 {len(items)}개, ↑↓ 이동, Space 선택/해제, "
            f"a 전체, i 반전, Enter 완료, 뒤로가기/나가기는 이동 후 Enter, Ctrl+C 취소):\n"
            f"{CART_LIST_HEADER}",
            choices=choices,
            focus_submit_values=frozenset({_BACK_TO_DELETE_MODE, _EXIT_CART_SELECTION}),
        )
        selected_items = tuple(value for value in selected if isinstance(value, CartItem))
        if selected_items:
            return selected_items
        if _BACK_TO_DELETE_MODE in selected:
            return "back"
        if _EXIT_CART_SELECTION in selected:
            return "exit"

        action = await prompt_cart_items_empty_action(prompts)
        if action == "back":
            return "back"
        if action == "exit":
            return "exit"


async def prompt_clear_cart_action(prompts: Prompts) -> ClearCartAction:
    selected = await prompts.select(
        "다음 작업을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("목록보기", value=_CLEAR_CART_LIST),
            Choice("전체 비우기", value=_CLEAR_CART_CLEAR),
            Choice("뒤로가기", value=_CLEAR_CART_BACK),
            Choice("나가기", value=_CLEAR_CART_EXIT),
        ],
    )
    if selected is _CLEAR_CART_LIST:
        return "list"
    if selected is _CLEAR_CART_CLEAR:
        return "clear"
    if selected is _CLEAR_CART_BACK:
        return "back"
    return "exit"


def format_deleted_cart_item(item: CartItem) -> str:
    option_text = item.option_text or "-"
    return f"{item.product_name} / {option_text} / {item.quantity}개"


async def prompt_quantity(prompts: Prompts, *, current_quantity: int) -> int:
    while True:
        value = (await prompts.text(f"새 수량을 입력하세요 (현재: {current_quantity}):")).strip()
        try:
            quantity = int(value)
        except ValueError:
            await prompts.print_message("수량은 숫자로 입력해주세요.")
            continue
        if quantity < 1:
            await prompts.print_message("수량은 1개 이상이어야 합니다.")
            continue
        return quantity


def format_cart_detail(item: CartItem) -> str:
    lines = [
        ("No", str(item.index)),
        ("상품명", item.product_name),
        ("옵션", item.option_text or "-"),
        ("수량", f"{item.quantity}개"),
        ("단가", item.unit_price or "-"),
        ("합계", item.total_price or item.unit_price or "-"),
        ("상품ID", item.product_id or "-"),
        ("벤더상품ID", item.vendor_item_id or "-"),
        ("아이템ID", item.item_id or "-"),
    ]
    if item.delivery_text:
        lines.append(("배송", item.delivery_text))
    return "\n".join(f"{label}: {value}" for label, value in lines)


async def prompt_list_detail_action(prompts: Prompts) -> ListDetailAction:
    selected = await prompts.select(
        "다음 작업을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("돌아가기", value=_BACK_TO_LIST),
            Choice("나가기", value=_EXIT_LIST_BROWSE),
        ],
    )
    if selected is _BACK_TO_LIST:
        return "back"
    return "exit"


async def run_cart_list_browse(
    terminal: Terminal,
    prompts: Prompts,
    items: tuple[CartItem, ...],
    *,
    exit_message: str,
) -> None:
    while True:
        try:
            selected_item = await prompt_cart_item(
                prompts,
                items,
                selection_prefix="상세 보기할 상품을 고르세요",
                browse=True,
            )
            if selected_item is None:
                terminal.echo(exit_message)
                return
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return

        terminal.echo(format_cart_detail(selected_item))

        try:
            action = await prompt_list_detail_action(prompts)
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return
        if action == "exit":
            terminal.echo(exit_message)
            return
