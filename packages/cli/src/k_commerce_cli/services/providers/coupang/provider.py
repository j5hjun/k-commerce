from __future__ import annotations

from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Provider
from k_commerce_cli.services.browser.nodriver import NodriverBrowser
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import LoginResult, LogoutResult, StatusResult

from .auth import CoupangAuthService


class CoupangProvider(Provider):
    def __init__(
        self,
        provider_name: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.terminal = terminal
        self.store = ProviderStore(
            ProviderPaths(provider_name, root_dir or Path.home() / ".k-commerce")
        )
        self._browser = NodriverBrowser()
        self._auth = CoupangAuthService(
            provider_name=provider_name,
            store=self.store,
            browser=self._browser,
            terminal=terminal,
        )

    async def login(self) -> LoginResult:
        return await self._auth.login()

    async def status(self) -> StatusResult:
        return await self._auth.status()

    async def logout(self) -> LogoutResult:
        return await self._auth.logout()

__all__ = ["CoupangProvider"]
