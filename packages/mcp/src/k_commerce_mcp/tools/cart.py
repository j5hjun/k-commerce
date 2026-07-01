from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ListCartResult,
)


async def cart_list(provider: str) -> ListCartResult:
    return await get_provider(provider).list_cart()


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
