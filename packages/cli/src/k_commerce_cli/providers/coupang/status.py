from pathlib import Path

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.types import StatusResult

from .browser import CoupangBrowser, CoupangBrowserSession
from .session_store import CoupangSessionStore


class CoupangStatusProvider:
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self.browser = CoupangBrowser()
        self._browser_session: CoupangBrowserSession | None = None
        self._configure_paths()

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.session_store = CoupangSessionStore(provider=self.name, root_dir=root_dir)

    async def status(self, root_dir: Path | None = None) -> StatusResult:
        self._configure_paths(root_dir)

        if not self.session_store.has_session():
            return StatusResult(
                provider=self.name,
                logged_in=False,
                message="쿠팡 로그인 상태가 아닙니다",
            )

        try:
            self._browser_session = await self.browser.launch(self.session_store.paths)
            await self.browser.open_home(self._browser_session)
            logged_in = await self.browser.is_logged_in(self._browser_session.tab)
            return StatusResult(
                provider=self.name,
                logged_in=logged_in,
                message=("쿠팡 로그인 상태입니다" if logged_in else "쿠팡 로그인 상태가 아닙니다"),
            )
        finally:
            await self._close_browser_session()

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None
