from k_commerce_cli.services.tools import invoke_tool


async def get_providers() -> list[str]:
    return await invoke_tool("get_providers", {})
