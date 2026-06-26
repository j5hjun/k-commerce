from k_commerce_cli.providers.registry import get_provider
from k_commerce_cli.types import LogoutResult


async def logout(provider: str) -> LogoutResult:
    return await get_provider(provider).logout()