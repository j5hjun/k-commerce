from pathlib import Path

import asyncclick as click

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.types import LoginResult

from .browser import CoupangBrowser, CoupangBrowserSession
from .credential_store import CoupangCredentials, CoupangCredentialStore
from .session_store import CoupangSessionStore


class CoupangLoginProvider:
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self.browser = CoupangBrowser()
        self._browser_session: CoupangBrowserSession | None = None
        self._configure_paths()

    def _configure_paths(self, root_dir: Path | None = None) -> None:
        self.credential_store = CoupangCredentialStore(provider=self.name, root_dir=root_dir)
        self.session_store = CoupangSessionStore(provider=self.name, root_dir=root_dir)

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

    def _load_credentials(self) -> CoupangCredentials | None:
        return self.credential_store.load()

    async def _restore_session(self):
        if not self.session_store.has_profile():
            return None

        self._browser_session = await self.browser.launch(self.session_store.paths)
        return self._browser_session

    async def _verify_session(self, session: CoupangBrowserSession) -> bool:
        await self.browser.open_home(session)
        return await self.browser.is_logged_in(session.tab)

    async def _login_with_credentials(self, credentials: CoupangCredentials) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(self.session_store.paths)

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
            self._browser_session = await self.browser.launch(self.session_store.paths)
            await self.browser.open_login_entry(self._browser_session)

        return await self.browser.wait_for_manual_login(self._browser_session)

    async def _persist_session(self, login_method: str) -> None:
        self.session_store.ensure_dir()
        if self._browser_session is not None:
            await self.browser.save_session(self._browser_session)
        self.session_store.write_metadata({"login_method": login_method})

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None
