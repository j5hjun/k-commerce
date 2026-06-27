from k_commerce_cli.services.registry import list_providers


async def get_providers() -> list[str]:
    return list_providers()
