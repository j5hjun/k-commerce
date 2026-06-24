from pathlib import Path

from k_commerce_cli.providers import LOGOUT_PROVIDERS
from k_commerce_cli.types import LogoutResult


async def logout(provider: str, root_dir: Path | None = None) -> LogoutResult:
    try:
        logout_provider = LOGOUT_PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc

    return await logout_provider.logout(root_dir=root_dir)
