import asyncio
import asyncclick as click
from dataclasses import dataclass

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab, Store
from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.types import (
    LoginResult,
    LogoutResult,
    StatusResult,
)

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = 'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'


@dataclass(frozen=True)
class LoginPageState:
    url: str
    has_login_link: bool
    has_mycoupang_link: bool


class CoupangAuthService:
    def __init__(
        self,
        provider_name: str,
        store: Store,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.store = store
        self.terminal = terminal
        self.browser = browser
        self._browser_session: BrowserSession | None = None

    @property
    def browser(self):
        return self._browser

    @browser.setter
    def browser(self, value) -> None:
        self._browser = value

    @property
    def _browser_session(self) -> BrowserSession | None:
        return self.__browser_session

    @_browser_session.setter
    def _browser_session(self, value: BrowserSession | None) -> None:
        self.__browser_session = value

    async def login(self) -> LoginResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 로그인을 시작합니다...")
        try:
            credentials = self._load_credentials()
            restored_session = await self._restore_session()

            if restored_session is not None and await self._verify_session(restored_session):
                return self._emit_login_result(
                    terminal,
                    LoginResult(provider=self.provider_name, success=True, message="쿠팡 로그인 성공"),
                )

            if credentials is not None:
                if terminal is not None:
                    terminal.info("자동 로그인을 시도합니다...")
                if await self._login_with_credentials(credentials):
                    await self._persist_session("automatic")
                    return self._emit_login_result(
                        terminal,
                        LoginResult(provider=self.provider_name, success=True, message="쿠팡 로그인 성공"),
                    )

            if terminal is not None:
                terminal.warn("브라우저에서 직접 로그인해주세요...")
            if not await self._wait_for_manual_login():
                return self._emit_login_result(
                    terminal,
                    LoginResult(provider=self.provider_name, success=False, message="쿠팡 로그인 실패"),
                )

            await self._persist_session("manual")
            return self._emit_login_result(
                terminal,
                LoginResult(provider=self.provider_name, success=True, message="쿠팡 로그인 성공"),
            )
        finally:
            await self._close_browser_session()

    async def status(self) -> StatusResult:
        terminal = self.terminal
        if not self.store.has_session():
            return self._emit_status_result(
                terminal,
                StatusResult(
                    provider=self.provider_name,
                    logged_in=False,
                    message="쿠팡 로그인 상태가 아닙니다",
                ),
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_home(self._browser_session)
            logged_in = await self._is_logged_in(self._browser_session.tab)
            return self._emit_status_result(
                terminal,
                StatusResult(
                    provider=self.provider_name,
                    logged_in=logged_in,
                    message=("쿠팡 로그인 상태입니다" if logged_in else "쿠팡 로그인 상태가 아닙니다"),
                ),
            )
        finally:
            await self._close_browser_session()

    async def logout(self) -> LogoutResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 로그아웃을 시작합니다...")

        if not self.store.has_session():
            return self._emit_logout_result(
                terminal,
                LogoutResult(
                    provider=self.provider_name,
                    success=True,
                    message="저장된 쿠팡 세션이 없습니다",
                ),
            )

        self.store.clear_session()
        return self._emit_logout_result(
            terminal,
            LogoutResult(provider=self.provider_name, success=True, message="쿠팡 로그아웃 완료"),
        )

    def _emit_login_result(
        self,
        terminal: Terminal | None,
        result: LoginResult,
    ) -> LoginResult:
        if terminal is not None:
            terminal.echo(result.message)
        if not result.success:
            raise click.ClickException(result.message)
        return result

    def _emit_status_result(
        self,
        terminal: Terminal | None,
        result: StatusResult,
    ) -> StatusResult:
        if terminal is not None:
            terminal.echo(result.message)
        return result

    def _emit_logout_result(
        self,
        terminal: Terminal | None,
        result: LogoutResult,
    ) -> LogoutResult:
        if terminal is not None:
            terminal.echo(result.message)
        return result

    def _load_credentials(self) -> Credentials | None:
        return self.store.load_credentials()

    async def _restore_session(self) -> BrowserSession | None:
        if not self.store.has_session():
            return None

        self._browser_session = await self.browser.launch(self.store.paths)
        return self._browser_session

    async def _verify_session(self, session: BrowserSession) -> bool:
        await self._open_home(session)
        return await self._is_logged_in(session.tab)

    async def _login_with_credentials(self, credentials: Credentials) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(self.store.paths)

        await self._open_login_entry(self._browser_session)
        submitted = await self._fill_login_form(
            self._browser_session,
            credentials.email,
            credentials.password,
        )
        if not submitted:
            return False

        return await self._wait_for_session_login(self._browser_session, poll_count=30)

    async def _wait_for_manual_login(self) -> bool:
        if self._browser_session is None:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_login_entry(self._browser_session)

        return await self._wait_for_session_login(self._browser_session)

    async def _persist_session(self, login_method: str) -> None:
        if self._browser_session is not None:
            await self.browser.save_session(
                self._browser_session,
                self.store.cookies_file,
            )
        self.store.write_session_metadata({"login_method": login_method})

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    async def _open_home(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_HOME_URL)

    async def _open_login_entry(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_LOGIN_URL)

    async def _is_logged_in(self, tab: BrowserTab) -> bool:
        page_state = await self._read_login_state(tab)
        if "login.coupang.com" in page_state.url:
            return False
        return (not page_state.has_login_link) and page_state.has_mycoupang_link

    async def _wait_for_session_login(
        self,
        session: BrowserSession,
        poll_count: int = 300,
    ) -> bool:
        for _ in range(poll_count):
            if await self._is_logged_in(self._login_tab(session)):
                return True
            await asyncio.sleep(1)
        return False

    async def _fill_login_form(
        self,
        session: BrowserSession,
        email: str,
        password: str,
    ) -> bool:
        email_input = await self.browser.select(
            session.tab, 'input[name="email"], input#login-email-input'
        )
        password_input = await self.browser.select(
            session.tab, 'input[name="password"], input#login-password-input'
        )
        submit_button = await self.browser.select(
            session.tab, 'button[type="submit"], .login__button'
        )
        if email_input is None or password_input is None or submit_button is None:
            return False

        await email_input.send_keys(email)
        await password_input.send_keys(password)
        await submit_button.click()
        if await self._dismiss_data_request_failure_modal(session.tab):
            await submit_button.click()
        return True

    async def _dismiss_data_request_failure_modal(self, tab: BrowserTab) -> bool:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return False

        await asyncio.sleep(0.5)
        try:
            result = await evaluate(
                """
                (() => {
                  const modal = [...document.querySelectorAll('div, p, span')]
                    .find((node) => node.textContent?.includes('데이터 요청에 실패하였습니다.'));
                  if (!modal) return false;

                  const confirmButton = [...document.querySelectorAll('button')]
                    .find((node) => node.textContent?.trim() === '확인');
                  if (!confirmButton) return false;

                  confirmButton.click();
                  return true;
                })()
                """
            )
        except Exception:
            return False

        return bool(result)

    def _login_tab(self, session: BrowserSession) -> BrowserTab:
        tabs = getattr(getattr(session, "browser", None), "tabs", None)
        candidates: list[BrowserTab] = []
        if isinstance(tabs, list):
            candidates.extend(reversed(tabs))

        main_tab = getattr(getattr(session, "browser", None), "main_tab", None)
        if main_tab is not None:
            candidates.append(main_tab)
        candidates.append(session.tab)

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            if "coupang.com" in str(getattr(candidate, "url", "")):
                return candidate

        for candidate in candidates:
            if hasattr(candidate, "select"):
                return candidate

        return session.tab

    async def _read_login_state(self, tab: BrowserTab) -> LoginPageState:
        login_link = await self.browser.select(tab, COUPANG_LOGIN_LINK_SELECTOR)
        my_coupang_link = await self.browser.select(tab, COUPANG_MYCOUPANG_SELECTOR)
        return LoginPageState(
            url=str(getattr(tab, "url", "")),
            has_login_link=login_link is not None,
            has_mycoupang_link=my_coupang_link is not None,
        )
