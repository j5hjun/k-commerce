from pathlib import Path

import asyncclick as click

from k_commerce_cli.types import LogoutResult

from .session_store import CoupangSessionStore


class CoupangLogoutProvider:
    name = "coupang"

    def __init__(self) -> None:
        self._configure_paths()

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.session_store = CoupangSessionStore(provider=self.name, root_dir=root_dir)

    async def logout(self, root_dir: Path | None = None) -> LogoutResult:
        self._configure_paths(root_dir)
        click.secho("쿠팡 로그아웃을 시작합니다...", fg="blue")

        if not self.session_store.has_session():
            return LogoutResult(
                provider=self.name,
                success=True,
                message="저장된 쿠팡 세션이 없습니다",
            )

        self.session_store.clear()
        return LogoutResult(provider=self.name, success=True, message="쿠팡 로그아웃 완료")
