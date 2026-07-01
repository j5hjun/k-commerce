from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Literal, TypeVar

import asyncclick as click
from questionary import Choice

from k_commerce_cli.base import Terminal
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.types import CartItem

T = TypeVar("T")

ListDetailAction = Literal["back", "exit"]

# questionary select가 각 항목 앞에 붙이는 포인터/선택 표시(»○   ) 너비
_QUESTIONARY_SELECT_PREFIX = "     "

PRODUCT_NAME_DISPLAY_WIDTH = 54
OPTION_TEXT_DISPLAY_WIDTH = 16

_EXIT_CART_SELECTION = object()
_CONTINUE_CART_SELECTION = object()
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


async def prompt_cart_item(
    prompts: Prompts,
    items: tuple[CartItem, ...],
    *,
    selection_prefix: str = "상품을 선택하세요",
    browse: bool = False,
) -> CartItem | None:
    choices: list[Choice] = []
    for item in items:
        choices.append(
            Choice(
                f"{item.index:>3}  "
                f"{_pad_display(item.product_name, PRODUCT_NAME_DISPLAY_WIDTH)}  "
                f"{_pad_display(item.option_text or '-', OPTION_TEXT_DISPLAY_WIDTH)}  "
                f"{item.quantity:>4}  "
                f"{item.total_price or item.unit_price or '-':>12}",
                value=item,
            )
        )
    choices.append(Choice("나가기", value=_EXIT_CART_SELECTION))

    selected = await prompts.select(
        f"{_cart_selection_prompt(selection_prefix, len(items), browse=browse)}\n"
        f"{CART_LIST_HEADER}",
        choices=choices,
    )
    if selected is _EXIT_CART_SELECTION or selected == "나가기":
        return None
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
