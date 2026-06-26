from pathlib import Path

import asyncclick as click

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.store import Credentials, ProviderStore
from k_commerce_cli.providers.base import AuthProvider
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult

from .browser import (
    BrowserTab,
    CoupangAuthBrowser,
    CoupangBrowserSession,
    CoupangSessionBrowser,
)


class CoupangAuthProvider(AuthProvider):
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self.session_browser = CoupangSessionBrowser()
        self.auth_browser = CoupangAuthBrowser(self.session_browser)
        self.browser = self
        self._browser_session: CoupangBrowserSession | None = None
        self._configure_paths()

    async def login(self, root_dir: Path | None = None) -> LoginResult:
        self._configure_paths(root_dir)
        click.secho("쿠팡 로그인을 시작합니다...", fg="blue")
        try:
            credentials = self._load_credentials()
            restored_session = await self._restore_session()

            if restored_session is not None and await self._verify_session(restored_session):
                return LoginResult(provider=self.name, success=True, message="쿠팡 로그인 성공")

            if credentials is not None:
                click.echo("자동 로그인을 시도합니다...")
                if await self._login_with_credentials(credentials):
                    await self._persist_session("automatic")
                    return LoginResult(provider=self.name, success=True, message="쿠팡 로그인 성공")

            click.echo("브라우저에서 직접 로그인해주세요...")
            if not await self._wait_for_manual_login():
                return LoginResult(provider=self.name, success=False, message="쿠팡 로그인 실패")

            await self._persist_session("manual")
            return LoginResult(provider=self.name, success=True, message="쿠팡 로그인 성공")
        finally:
            await self._close_browser_session()

    async def status(self, root_dir: Path | None = None) -> StatusResult:
        self._configure_paths(root_dir)

        if not self.store.has_session():
            return StatusResult(
                provider=self.name,
                logged_in=False,
                message="쿠팡 로그인 상태가 아닙니다",
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self.browser.open_home(self._browser_session)
            logged_in = await self.browser.is_logged_in(self._browser_session.tab)
            return StatusResult(
                provider=self.name,
                logged_in=logged_in,
                message=("쿠팡 로그인 상태입니다" if logged_in else "쿠팡 로그인 상태가 아닙니다"),
            )
        finally:
            await self._close_browser_session()

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

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.store = ProviderStore(
            ProviderPaths(self.name, root_dir or Path.home() / ".k-commerce")
        )

    def _load_credentials(self) -> Credentials | None:
        return self.store.load_credentials()

    async def _restore_session(self) -> CoupangBrowserSession | None:
        if not self.store.has_session():
            return None

        self._browser_session = await self.browser.launch(self.store.paths)
        return self._browser_session

    async def _verify_session(self, session: CoupangBrowserSession) -> bool:
        await self.browser.open_home(session)
        return await self.browser.is_logged_in(session.tab)

    async def _login_with_credentials(self, credentials: Credentials) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(self.store.paths)

        await self.browser.open_login_entry(self._browser_session)
        submitted = await self.browser.fill_login_form(
            self._browser_session,
            credentials.email,
            credentials.password,
        )
        if not submitted:
            return False

        return await self.browser.wait_for_manual_login(self._browser_session, poll_count=30)

    async def _wait_for_manual_login(self) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self.browser.open_login_entry(self._browser_session)

        return await self.browser.wait_for_manual_login(self._browser_session)

    async def _persist_session(self, login_method: str) -> None:
        if self._browser_session is not None:
            await self.browser.save_session(self._browser_session)
        self.store.write_session_metadata({"login_method": login_method})

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    async def launch(self, paths: ProviderPaths) -> CoupangBrowserSession:
        return await self.session_browser.launch(paths)

    async def open_home(self, session: CoupangBrowserSession) -> None:
        await self.auth_browser.open_home(session)

    async def open_login(self, session: CoupangBrowserSession) -> None:
        await self.auth_browser.open_login(session)

    async def open_login_entry(self, session: CoupangBrowserSession) -> None:
        await self.auth_browser.open_login_entry(session)

    async def is_logged_in(self, tab: BrowserTab) -> bool:
        return await self.auth_browser.is_logged_in(tab)

    async def wait_for_manual_login(
        self,
        session: CoupangBrowserSession,
        poll_count: int = 300,
    ) -> bool:
        return await self.auth_browser.wait_for_manual_login(session, poll_count=poll_count)

    async def fill_login_form(
        self,
        session: CoupangBrowserSession,
        email: str,
        password: str,
    ) -> bool:
        return await self.auth_browser.fill_login_form(session, email, password)

    async def save_session(self, session: CoupangBrowserSession) -> None:
        await self.session_browser.save_session(session)

    async def close(self, session: CoupangBrowserSession) -> None:
        await self.session_browser.close(session)

    def _active_tab(self, session: CoupangBrowserSession) -> BrowserTab:
        return self.session_browser._active_tab(session)
