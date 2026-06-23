from pathlib import Path

import asyncclick as click
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .browser import COUPANG_HOME_URL, COUPANG_LOGIN_URL, CoupangBrowser, first_product_link_selector
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
        self.credentials_path = (
            Path.home() / ".k-commerce" / "coupang" / "credentials.json"
        )

    @property
    def credentials_path(self) -> Path:
        return self._credentials_path

    @credentials_path.setter
    def credentials_path(self, value: Path) -> None:
        self._credentials_path = value
        self.credential_store = CoupangCredentialStore(value)
        self.session_store = CoupangSessionStore(value.parent)

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
        if not self.session_store.has_storage_state():
            return None

        self._browser_session = await self.browser.launch(
            storage_state_path=self.session_store.storage_state_path
        )
        return self._browser_session

    async def _verify_session(self, session: CoupangBrowserSession) -> bool:
        await session.page.goto(COUPANG_HOME_URL)
        return await self._current_page_is_logged_in(session.page)

    async def _login_with_credentials(self, credentials: CoupangCredentials) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch()

        page = self._browser_session.page
        await self._open_login_entry(page)
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

        return await self._current_page_is_logged_in(page)

    async def _wait_for_manual_login(self) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch()
            await self._open_login_entry(self._browser_session.page)

        page = self._browser_session.page

        if "login.coupang.com" in page.url:
            try:
                await page.wait_for_url(
                    lambda url: "login.coupang.com" not in str(url),
                    timeout=300_000,
                )
            except PlaywrightTimeoutError:
                return False

        for _ in range(300):
            page = self._select_active_page(page)
            if await self._current_page_is_logged_in(page):
                return True
            try:
                await page.wait_for_timeout(1000)
            except PlaywrightError:
                page = self._select_active_page(page)

        return False

    async def _persist_session(self, login_method: str) -> None:
        self.session_store.ensure_dir()
        if self._browser_session is None:
            self.session_store.storage_state_path.write_text("{}", encoding="utf-8")
        else:
            await self._browser_session.context.storage_state(
                path=self.session_store.storage_state_path
            )
        self.session_store.write_metadata({"login_method": login_method})

    async def _current_page_is_logged_in(self, page) -> bool:
        if "login.coupang.com" in page.url:
            return False

        login_link = await page.query_selector('a[href*="login.coupang.com"]')
        my_coupang_link = await page.query_selector(
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
        )
        return login_link is None and my_coupang_link is not None

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self._browser_session.page.close()
        finally:
            try:
                await self._browser_session.context.close()
            finally:
                try:
                    await self._browser_session.browser.close()
                finally:
                    stop = getattr(self._browser_session.playwright, "stop", None)
                    if stop is not None:
                        await stop()
                    self._browser_session = None

    def _select_active_page(self, page):
        if self._browser_session is None:
            return page

        is_closed = getattr(page, "is_closed", None)
        if callable(is_closed) and not is_closed():
            return page

        for candidate in reversed(self._browser_session.context.pages):
            candidate_is_closed = getattr(candidate, "is_closed", None)
            if callable(candidate_is_closed) and not candidate_is_closed():
                return candidate

        return page

    async def _open_login_entry(self, page) -> None:
        try:
            await page.goto(COUPANG_LOGIN_URL)
            return
        except PlaywrightError:
            await page.goto(COUPANG_HOME_URL)
            await page.click(first_product_link_selector())
