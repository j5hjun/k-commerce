import os
from pathlib import Path

import asyncclick as click
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .browser import CoupangBrowser
from .browser import (
    CoupangBrowserSession,
)
from .credential_store import CoupangCredentialStore, CoupangCredentials
from .session_store import CoupangSessionStore
from k_commerce_cli.types import LoginResult


class CoupangLoginProvider:
    name = "coupang"

    def __init__(self) -> None:
        self.browser = CoupangBrowser()
        self._browser_session: CoupangBrowserSession | None = None
        self.credentials_path = Path.home() / ".coupang-session" / "credentials.json"
        self.session_store = CoupangSessionStore(Path.home() / ".k-commerce" / "coupang")

    @property
    def credentials_path(self) -> Path:
        return self._credentials_path

    @credentials_path.setter
    def credentials_path(self, value: Path) -> None:
        self._credentials_path = value
        self.credential_store = CoupangCredentialStore(value)

    async def login(self) -> LoginResult:
        click.secho("쿠팡 로그인을 시작합니다...", fg="blue")
        try:
            credentials = self._load_credentials()
            restored_session = await self._restore_session()

            if restored_session is not None and await self._verify_session(restored_session):
                return LoginResult(
                    provider=self.name,
                    success=True,
                    message="쿠팡 로그인 성공",
                )

            if credentials is not None:
                click.echo("자동 로그인을 시도합니다...")
                if await self._login_with_credentials(credentials):
                    await self._persist_session("automatic")
                    return LoginResult(
                        provider=self.name,
                        success=True,
                        message="쿠팡 로그인 성공",
                    )

            click.echo("브라우저에서 직접 로그인해주세요...")
            if not await self._wait_for_manual_login():
                return LoginResult(
                    provider=self.name,
                    success=False,
                    message="쿠팡 로그인 실패",
                )

            await self._persist_session("manual")
            return LoginResult(
                provider=self.name,
                success=True,
                message="쿠팡 로그인 성공",
            )
        finally:
            await self._close_browser_session()

    def _load_credentials(self) -> CoupangCredentials | None:
        return self.credential_store.load()

    async def _restore_session(self):
        if self._uses_chrome_persistent_session():
            profile_dir = self.browser.chrome_profile_dir(self.session_store.base_dir)
            if not profile_dir.is_dir():
                return None

            self._browser_session = await self.browser.launch(
                preferred="chrome",
                base_dir=self.session_store.base_dir,
            )
            return self._browser_session

        if not self.session_store.has_storage_state():
            return None

        self._browser_session = await self.browser.launch(
            preferred="firefox",
            storage_state_path=self.session_store.storage_state_path
        )
        return self._browser_session

    async def _verify_session(self, session: CoupangBrowserSession) -> bool:
        await self.browser.open_home(session)
        return await self.browser.is_logged_in(session.page)

    async def _login_with_credentials(self, credentials: CoupangCredentials) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(
                preferred=self._preferred_browser(),
                base_dir=self.session_store.base_dir,
            )

        page = self._browser_session.page
        await self.browser.open_login_entry(self._browser_session)
        await page.fill(
            'input[name="email"], input#login-email-input',
            credentials.email,
        )
        await page.fill(
            'input[name="password"], input#login-password-input',
            credentials.password,
        )
        await page.click('button[type="submit"], .login__button')

        try:
            await page.wait_for_url(
                lambda url: "login.coupang.com" not in str(url),
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            return False

        return await self.browser.is_logged_in(page)

    async def _wait_for_manual_login(self) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(
                preferred=self._preferred_browser(),
                base_dir=self.session_store.base_dir,
            )
            await self.browser.open_login_entry(self._browser_session)

        return await self.browser.wait_for_manual_login(self._browser_session)

    async def _persist_session(self, login_method: str) -> None:
        self.session_store.ensure_dir()
        if self._browser_session is None:
            self.session_store.storage_state_path.write_text("{}", encoding="utf-8")
        elif self._uses_chrome_persistent_session():
            pass
        else:
            await self.browser.save_storage_state(
                self._browser_session,
                self.session_store.storage_state_path,
            )
        self.session_store.write_metadata({"login_method": login_method})

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    def _preferred_browser(self) -> str:
        return "chrome" if self._uses_chrome_persistent_session() else "firefox"

    def _uses_chrome_persistent_session(self) -> bool:
        return os.getenv("COUPANG_BROWSER") == "chrome"
