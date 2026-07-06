from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import DeliveryTrackingResult, OrderResult


async def order_list(
    provider: str,
    refresh: bool = False,
    failed_only: bool = False,
) -> OrderResult:
    return await get_provider(provider).list_orders(
        refresh=refresh,
        failed_only=failed_only,
    )


async def order_delivery_tracking(
    provider: str,
    order_id: int,
    shipment_box_id: str,
) -> DeliveryTrackingResult:
    return await get_provider(provider).get_delivery_tracking(
        order_id=order_id,
        shipment_box_id=shipment_box_id,
    )
