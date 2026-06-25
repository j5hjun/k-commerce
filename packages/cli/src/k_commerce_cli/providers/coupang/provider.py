from pathlib import Path

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.coupang.login import CoupangLoginProvider
from k_commerce_cli.providers.coupang.logout import CoupangLogoutProvider
from k_commerce_cli.providers.coupang.status import CoupangStatusProvider
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult


class CoupangProvider:
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self._login_provider = CoupangLoginProvider()
        self._status_provider = CoupangStatusProvider()
        self._logout_provider = CoupangLogoutProvider()

    async def login(self, root_dir: Path | None = None) -> LoginResult:
        return await self._login_provider.login(root_dir=root_dir)

    async def status(self, root_dir: Path | None = None) -> StatusResult:
        return await self._status_provider.status(root_dir=root_dir)

    async def logout(self, root_dir: Path | None = None) -> LogoutResult:
        return await self._logout_provider.logout(root_dir=root_dir)
