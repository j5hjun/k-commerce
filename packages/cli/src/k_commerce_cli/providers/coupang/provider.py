from __future__ import annotations

from pathlib import Path

from k_commerce_cli.providers.base import Provider, Terminal
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult

from .auth import CoupangAuthService


class CoupangProvider(Provider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        self._auth = CoupangAuthService(provider_name=provider_name)

    @property
    def browser(self):
        return self._auth.browser

    @browser.setter
    def browser(self, value) -> None:
        self._auth.browser = value

    @property
    def store(self):
        return self._auth.store

    @store.setter
    def store(self, value) -> None:
        self._auth.store = value

    async def login(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LoginResult:
        return await self._auth.login(root_dir=root_dir, terminal=terminal)

    async def status(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> StatusResult:
        return await self._auth.status(root_dir=root_dir, terminal=terminal)

    async def logout(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LogoutResult:
        return await self._auth.logout(root_dir=root_dir, terminal=terminal)

__all__ = ["CoupangProvider"]
