from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import OrderResult


async def order_list(
    provider: str,
    refresh: bool = False,
    failed_only: bool = False,
) -> OrderResult:
    return await get_provider(provider).list_orders(
        refresh=refresh,
        failed_only=failed_only,
    )
