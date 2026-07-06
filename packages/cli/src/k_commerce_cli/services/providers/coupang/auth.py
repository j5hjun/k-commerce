import asyncio
from dataclasses import dataclass

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab, Store
from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.types import (
    LoginResult,
    LogoutResult,
    ProviderName,
    StatusResult,
)
from k_commerce_cli.services.providers.coupang.result_metadata import (
    BROWSER_CLOSED_METADATA,
    LOGIN_REQUIRED_METADATA,
    is_browser_closed_error,
)

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = 'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
COUPANG_ACCESS_BLOCKED_MESSAGE = "쿠팡 접근이 차단되었습니다"
COUPANG_DATA_REQUEST_FAILED_MESSAGE = "쿠팡 데이터 요청에 실패했습니다"


@dataclass(frozen=True)
class LoginPageState:
    url: str
    has_login_link: bool
    has_mycoupang_link: bool
    access_blocked: bool = False


class CoupangAuthService:
    def __init__(
        self,
        provider: ProviderName,
        store: Store,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider = provider
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
                    LoginResult(provider=self.provider, success=True, message="쿠팡 로그인 성공"),
                )

            if credentials is not None:
                if terminal is not None:
                    terminal.info("자동 로그인을 시도합니다...")
                if await self._login_with_credentials(credentials):
                    await self._persist_session("automatic")
                    return self._emit_login_result(
                        terminal,
                        LoginResult(provider=self.provider, success=True, message="쿠팡 로그인 성공"),
                    )

            if terminal is not None:
                terminal.warn("브라우저에서 직접 로그인해주세요...")
            if not await self._wait_for_manual_login():
                return self._emit_login_result(
                    terminal,
                    LoginResult(
                        provider=self.provider,
                        success=False,
                        message="쿠팡 로그인 실패",
                        error_code="login_failed",
                        retryable=True,
                    ),
                )

            await self._persist_session("manual")
            return self._emit_login_result(
                terminal,
                LoginResult(provider=self.provider, success=True, message="쿠팡 로그인 성공"),
            )
        except RuntimeError as exc:
            if is_browser_closed_error(exc):
                return self._emit_login_result(
                    terminal,
                    LoginResult(
                        provider=self.provider,
                        success=False,
                        message="브라우저가 닫혀 로그인을 완료하지 못했습니다.",
                        error_code=BROWSER_CLOSED_METADATA.error_code,
                        retryable=BROWSER_CLOSED_METADATA.retryable,
                        next_tools=BROWSER_CLOSED_METADATA.next_tools,
                    ),
                )
            if str(exc) not in {
                COUPANG_ACCESS_BLOCKED_MESSAGE,
                COUPANG_DATA_REQUEST_FAILED_MESSAGE,
            }:
                raise
            return self._emit_login_result(
                terminal,
                LoginResult(
                    provider=self.provider,
                    success=False,
                    message=str(exc),
                    error_code=self._login_error_code(str(exc)),
                    retryable=True,
                ),
            )
        finally:
            await self._close_browser_session()

    async def status(self) -> StatusResult:
        terminal = self.terminal
        if not self.store.has_session():
            return self._emit_status_result(
                terminal,
                StatusResult(
                    provider=self.provider,
                    logged_in=False,
                    message="쿠팡 로그인 상태가 아닙니다",
                    error_code=LOGIN_REQUIRED_METADATA.error_code,
                    retryable=LOGIN_REQUIRED_METADATA.retryable,
                    next_tools=LOGIN_REQUIRED_METADATA.next_tools,
                ),
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_home(self._browser_session)
            logged_in = await self._is_logged_in(self._browser_session.tab)
            return self._emit_status_result(
                terminal,
                StatusResult(
                    provider=self.provider,
                    logged_in=logged_in,
                    message=("쿠팡 로그인 상태입니다" if logged_in else "쿠팡 로그인 상태가 아닙니다"),
                    error_code="" if logged_in else LOGIN_REQUIRED_METADATA.error_code,
                    retryable=False,
                    next_tools=() if logged_in else LOGIN_REQUIRED_METADATA.next_tools,
                ),
            )
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._emit_status_result(
                terminal,
                StatusResult(
                    provider=self.provider,
                    logged_in=False,
                    message="브라우저가 닫혀 로그인 상태를 확인하지 못했습니다.",
                    error_code=BROWSER_CLOSED_METADATA.error_code,
                    retryable=BROWSER_CLOSED_METADATA.retryable,
                    next_tools=BROWSER_CLOSED_METADATA.next_tools,
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
                    provider=self.provider,
                    success=True,
                    message="저장된 쿠팡 세션이 없습니다",
                ),
            )

        self.store.clear_session()
        return self._emit_logout_result(
            terminal,
            LogoutResult(provider=self.provider, success=True, message="쿠팡 로그아웃 완료"),
        )

    def _emit_login_result(
        self,
        terminal: Terminal | None,
        result: LoginResult,
    ) -> LoginResult:
        if terminal is not None:
            if result.success:
                terminal.success(result.message)
        if not result.success:
            if terminal is not None:
                terminal.abort(result.message)
        return result

    def _login_error_code(self, message: str) -> str:
        if message == COUPANG_ACCESS_BLOCKED_MESSAGE:
            return "access_blocked"
        if message == COUPANG_DATA_REQUEST_FAILED_MESSAGE:
            return "data_request_failed"
        return "login_failed"

    def _emit_status_result(
        self,
        terminal: Terminal | None,
        result: StatusResult,
    ) -> StatusResult:
        if terminal is not None:
            if result.logged_in:
                terminal.success(result.message)
            else:
                terminal.warn(result.message)
        return result

    def _emit_logout_result(
        self,
        terminal: Terminal | None,
        result: LogoutResult,
    ) -> LogoutResult:
        if terminal is not None:
            terminal.success(result.message)
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

        return await self._wait_for_credentials_login(self._browser_session)

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
        if page_state.access_blocked:
            raise RuntimeError(COUPANG_ACCESS_BLOCKED_MESSAGE)
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

    async def _wait_for_credentials_login(
        self,
        session: BrowserSession,
        poll_count: int = 30,
    ) -> bool:
        for _ in range(poll_count):
            if await self._has_data_request_failure_modal(session.tab):
                raise RuntimeError(COUPANG_DATA_REQUEST_FAILED_MESSAGE)
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
            await self._raise_if_blocked_page(session.tab)
            return False

        await email_input.send_keys(email)
        await password_input.send_keys(password)
        await submit_button.click()
        if await self._has_data_request_failure_modal(session.tab):
            raise RuntimeError(COUPANG_DATA_REQUEST_FAILED_MESSAGE)
        return True

    async def _has_data_request_failure_modal(self, tab: BrowserTab) -> bool:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return False

        await asyncio.sleep(0.5)
        try:
            result = await evaluate(
                """
                (() => {
                  const modal = [...document.querySelectorAll('div, p, span')]
                    .find((node) => /데이터\\s*요청.*실패\\s*하였습니다/.test(node.textContent || ''));
                  if (!modal) return false;
                  return true;
                })()
                """
            )
        except Exception:
            return False

        return bool(result)

    def _login_tab(self, session: BrowserSession) -> BrowserTab:
        runtime = getattr(session, "browser", None)
        candidates: list[BrowserTab] = []
        if runtime is not None:
            tabs = getattr(runtime, "tabs", None)
            if isinstance(tabs, list):
                candidates.extend(reversed(tabs))

            main_tab = None
            try:
                main_tab = runtime.main_tab  # type: ignore[attr-defined]
            except (StopIteration, RuntimeError):
                main_tab = None
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
        text = await self._read_page_text(tab)
        return LoginPageState(
            url=str(getattr(tab, "url", "")),
            has_login_link=login_link is not None,
            has_mycoupang_link=my_coupang_link is not None,
            access_blocked=self._is_access_blocked(str(getattr(tab, "url", "")), text),
        )

    async def _read_page_text(self, tab: BrowserTab) -> str:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return ""
        try:
            value = await evaluate("document.body?.innerText || document.documentElement?.innerText || ''")
        except Exception:
            return ""
        return str(value)

    async def _raise_if_blocked_page(self, tab: BrowserTab) -> None:
        url = str(getattr(tab, "url", ""))
        text = await self._read_page_text(tab)
        if self._is_access_denied(url, text):
            raise RuntimeError(COUPANG_ACCESS_BLOCKED_MESSAGE)
        if self._is_data_request_failed(text):
            raise RuntimeError(COUPANG_DATA_REQUEST_FAILED_MESSAGE)

    def _is_access_blocked(self, url: str, text: str) -> bool:
        return self._is_access_denied(url, text) or self._is_data_request_failed(text)

    def _is_access_denied(self, url: str, text: str) -> bool:
        # TODO: This is unit-covered, but still needs live smoke reproduction.
        value = f"{url}\n{text}".lower()
        return (
            "access denied" in value
            or "errors.edgesuite.net" in value
        )

    def _is_data_request_failed(self, text: str) -> bool:
        compact = "".join(text.split())
        return "데이터요청" in compact and "실패하였습니다" in compact
