from __future__ import annotations

from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Provider
from k_commerce_cli.services.browser.nodriver import NodriverBrowser
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult

from .auth import CoupangAuthService


class CoupangProvider(Provider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        self.store = ProviderStore(ProviderPaths(provider_name, Path.home() / ".k-commerce"))
        self._browser = NodriverBrowser()
        self._auth = CoupangAuthService(
            provider_name=provider_name,
            store=self.store,
            browser=self._browser,
        )

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.store = ProviderStore(
            ProviderPaths(self.provider_name, root_dir or Path.home() / ".k-commerce")
        )
        self._auth.store = self.store

    @property
    def browser(self):
        return self._browser

    @browser.setter
    def browser(self, value) -> None:
        self._browser = value
        self._auth.browser = value

    async def login(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LoginResult:
        self._configure_paths(root_dir)
        return await self._auth.login(root_dir=root_dir, terminal=terminal)

    async def status(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> StatusResult:
        self._configure_paths(root_dir)
        return await self._auth.status(root_dir=root_dir, terminal=terminal)

    async def logout(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LogoutResult:
        self._configure_paths(root_dir)
        return await self._auth.logout(root_dir=root_dir, terminal=terminal)

__all__ = ["CoupangProvider"]
