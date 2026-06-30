from questionary import Choice

from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.types import CartItem

PRODUCT_NAME_DISPLAY_WIDTH = 54
OPTION_TEXT_DISPLAY_WIDTH = 16
_EXIT_CART_SELECTION = object()


async def prompt_cart_item(
    prompts: Prompts,
    items: tuple[CartItem, ...],
    *,
    message: str,
) -> CartItem | None:
    choices: list[Choice] = []
    for item in items:
        choices.append(
            Choice(
                f"{item.index:>3}  {_pad_display(item.product_name, PRODUCT_NAME_DISPLAY_WIDTH)}  {_pad_display(item.option_text or '-', OPTION_TEXT_DISPLAY_WIDTH)}  {item.quantity:>4}  {item.total_price or item.unit_price or '-':>12}",
                value=item,
            )
        )
    choices.append(Choice("나가기", value=_EXIT_CART_SELECTION))

    selected = await prompts.select(
        f"{message}\n"
        f"  {'#':>3}  {_pad_display('상품명', PRODUCT_NAME_DISPLAY_WIDTH)}  {_pad_display('옵션', OPTION_TEXT_DISPLAY_WIDTH)}  {'수량':>4}  {'가격':>12}",
        choices=choices,
    )
    if selected is _EXIT_CART_SELECTION or selected == "나가기":
        return None
    return selected


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
