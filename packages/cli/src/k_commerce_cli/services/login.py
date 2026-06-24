from pathlib import Path

from k_commerce_cli.providers import LOGIN_PROVIDERS
from k_commerce_cli.types import LoginResult


async def login(provider: str, root_dir: Path | None = None) -> LoginResult:
    try:
        login_provider = LOGIN_PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc

    return await login_provider.login(root_dir=root_dir)
