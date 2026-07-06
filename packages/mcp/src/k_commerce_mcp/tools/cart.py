from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartItem,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ListCartResult,
)


def _normalize_match_text(value: str) -> str:
    return "".join(value.lower().split())


def _resolve_cart_item(
    items: tuple[CartItem, ...],
    *,
    item_index: int = 0,
    product_name: str = "",
    option_text: str = "",
) -> CartItem | None:
    if item_index > 0:
        return next((item for item in items if item.index == item_index), None)

    normalized_name = _normalize_match_text(product_name)
    normalized_option = _normalize_match_text(option_text)

    if not normalized_name:
        return None

    matches = [
        item
        for item in items
        if normalized_name in _normalize_match_text(item.product_name)
    ]
    if normalized_option:
        matches = [
            item
            for item in matches
            if normalized_option in _normalize_match_text(item.option_text)
        ]
    if len(matches) == 1:
        return matches[0]
    return None


async def cart_list(provider: str, refresh: bool = False) -> ListCartResult:
    return await get_provider(provider).list_cart(refresh=refresh)


async def cart_update_quantity(
    provider: str,
    quantity: int,
    product_id: str = "",
    vendor_item_id: str = "",
    item_id: str = "",
) -> CartQuantityUpdateResult:
    request = CartQuantityUpdateRequest(
        quantity=quantity,
        product_id=product_id,
        vendor_item_id=vendor_item_id,
        item_id=item_id,
    )
    return await get_provider(provider).update_cart_quantity(request)


async def cart_update_quantity_smart(
    provider: str,
    quantity: int,
    item_index: int = 0,
    product_name: str = "",
    option_text: str = "",
) -> CartQuantityUpdateResult:
    cart = await get_provider(provider).list_cart()
    if not cart.success:
        return CartQuantityUpdateResult(
            provider=provider,
            success=False,
            message=cart.message,
            quantity=quantity,
            notice="장바구니를 먼저 읽지 못했습니다.",
        )

    item = _resolve_cart_item(
        cart.items,
        item_index=item_index,
        product_name=product_name,
        option_text=option_text,
    )
    if item is None:
        target = f"{item_index}번 상품" if item_index > 0 else product_name or option_text
        return CartQuantityUpdateResult(
            provider=provider,
            success=False,
            message=(
                f"장바구니에서 '{target}'에 해당하는 상품을 정확히 찾지 못했습니다. "
                "cart_list 결과의 index 또는 상품명을 다시 확인해주세요."
            ),
            quantity=quantity,
            notice="식별 가능한 장바구니 항목이 필요합니다.",
        )

    request = CartQuantityUpdateRequest(
        quantity=quantity,
        product_id=item.product_id,
        vendor_item_id=item.vendor_item_id,
        item_id=item.item_id,
    )
    return await get_provider(provider).update_cart_quantity(request)


async def cart_delete_item(
    provider: str,
    product_id: str = "",
    vendor_item_id: str = "",
    item_id: str = "",
) -> CartDeleteResult:
    request = CartDeleteRequest(
        product_id=product_id,
        vendor_item_id=vendor_item_id,
        item_id=item_id,
    )
    return await get_provider(provider).delete_cart_item(request)


async def cart_delete_items(
    provider: str,
    items: list[CartDeleteRequest],
) -> CartDeleteResult:
    return await get_provider(provider).delete_cart_items(tuple(items))


async def cart_clear(provider: str) -> CartDeleteResult:
    return await get_provider(provider).clear_cart()
