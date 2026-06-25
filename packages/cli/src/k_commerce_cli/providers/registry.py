from pathlib import Path

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.coupang import (
    CoupangLoginProvider,
    CoupangLogoutProvider,
    CoupangStatusProvider,
)
from k_commerce_cli.providers.types import AuthProvider


class CoupangProvider:
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self._login_provider = CoupangLoginProvider()
        self._status_provider = CoupangStatusProvider()
        self._logout_provider = CoupangLogoutProvider()

    async def login(self, root_dir: Path | None = None):
        return await self._login_provider.login(root_dir=root_dir)

    async def status(self, root_dir: Path | None = None):
        return await self._status_provider.status(root_dir=root_dir)

    async def logout(self, root_dir: Path | None = None):
        return await self._logout_provider.logout(root_dir=root_dir)


PROVIDERS: dict[str, AuthProvider] = {
    ProviderName.COUPANG: CoupangProvider(),
}
