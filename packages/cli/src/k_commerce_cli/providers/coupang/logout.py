from pathlib import Path

import asyncclick as click

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.store import ProviderStore
from k_commerce_cli.types import LogoutResult


class CoupangLogoutProvider:
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self._configure_paths()

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.store = ProviderStore(ProviderPaths(self.name, root_dir or Path.home() / ".k-commerce"))

    async def logout(self, root_dir: Path | None = None) -> LogoutResult:
        self._configure_paths(root_dir)
        click.secho("쿠팡 로그아웃을 시작합니다...", fg="blue")

        if not self.store.has_session():
            return LogoutResult(
                provider=self.name,
                success=True,
                message="저장된 쿠팡 세션이 없습니다",
            )

        self.store.clear_session()
        return LogoutResult(provider=self.name, success=True, message="쿠팡 로그아웃 완료")
