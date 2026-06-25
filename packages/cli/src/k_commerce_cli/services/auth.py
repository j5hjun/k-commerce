from pathlib import Path
from typing import Literal

from k_commerce_cli.providers.registry import PROVIDERS
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult

AuthAction = Literal["login", "status", "logout"]


def _get_provider(provider: str):
    try:
        return PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc


async def login(provider: str, root_dir: Path | None = None) -> LoginResult:
    auth_provider = _get_provider(provider)
    return await auth_provider.login(root_dir=root_dir)


async def status(provider: str, root_dir: Path | None = None) -> StatusResult:
    auth_provider = _get_provider(provider)
    return await auth_provider.status(root_dir=root_dir)


async def logout(provider: str, root_dir: Path | None = None) -> LogoutResult:
    auth_provider = _get_provider(provider)
    return await auth_provider.logout(root_dir=root_dir)
