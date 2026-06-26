from k_commerce_cli.providers.registry import list_providers


async def get_providers() -> list[str]:
    return list_providers()