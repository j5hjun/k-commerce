from k_commerce_cli.providers.registry import get_provider
from k_commerce_cli.types import LoginResult


async def login(provider: str) -> LoginResult:
    return await get_provider(provider).auth.login()
