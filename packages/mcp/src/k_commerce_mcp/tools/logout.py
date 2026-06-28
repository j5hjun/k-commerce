from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import LogoutResult


async def logout(provider: str) -> LogoutResult:
    return await get_provider(provider).logout()
