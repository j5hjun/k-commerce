from k_commerce_cli.services.types import CartItem

COUPANG_CART_URL = "https://cart.coupang.com/cartView.pang"
PRODUCT_NAME_DISPLAY_WIDTH = 54
OPTION_TEXT_DISPLAY_WIDTH = 16


def format_cart_list(items: tuple[CartItem, ...]) -> str:
    if not items:
        return "장바구니에 담긴 상품이 없습니다."

    lines = [
        f"장바구니 상품 ({len(items)}건):",
        "",
        f"  {'#':>3}  {_pad_display('상품명', PRODUCT_NAME_DISPLAY_WIDTH)}  {_pad_display('옵션', OPTION_TEXT_DISPLAY_WIDTH)}  {'수량':>4}  {'가격':>12}",
    ]
    for item in items:
        product_name = item.product_name
        option_text = item.option_text
        lines.append(
            f"  {item.index:>3}  {_pad_display(product_name, PRODUCT_NAME_DISPLAY_WIDTH)}  {_pad_display(option_text or '-', OPTION_TEXT_DISPLAY_WIDTH)}  {item.quantity:>4}  {item.total_price or item.unit_price or '-':>12}"
        )
    return "\n".join(lines)


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
