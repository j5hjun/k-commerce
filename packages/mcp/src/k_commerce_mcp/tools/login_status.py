from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.types import StatusResult


async def login_status(provider: str) -> StatusResult:
    return await get_provider(provider).status()
