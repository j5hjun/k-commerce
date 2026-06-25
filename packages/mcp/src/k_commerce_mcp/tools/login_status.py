from k_commerce_cli.services import login_status as run_login_status


async def login_status(provider: str) -> str:
    result = await run_login_status(provider)
    return result.message
