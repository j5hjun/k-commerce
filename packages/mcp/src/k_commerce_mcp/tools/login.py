from k_commerce_cli.services import login as run_login


async def login(provider: str) -> str:
    result = await run_login(provider)
    return result.message
