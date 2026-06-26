from __future__ import annotations

from k_commerce_cli.types import LoginPageState

from .session import BrowserTab, CoupangBrowserSession, CoupangSessionBrowser

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = 'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'


class CoupangAuthBrowser:
    def __init__(self, session_browser: CoupangSessionBrowser) -> None:
        self.session_browser = session_browser

    async def open_home(self, session: CoupangBrowserSession) -> None:
        await session.tab.get(COUPANG_HOME_URL)

    async def open_login(self, session: CoupangBrowserSession) -> None:
        await session.tab.get(COUPANG_LOGIN_URL)

    async def open_login_entry(self, session: CoupangBrowserSession) -> None:
        await self.open_login(session)

    async def is_logged_in(self, tab: BrowserTab) -> bool:
        page_state = await self._read_login_state(tab)
        page_url = page_state.url
        if "login.coupang.com" in page_url:
            return False

        return (not page_state.has_login_link) and page_state.has_mycoupang_link

    async def wait_for_manual_login(
        self,
        session: CoupangBrowserSession,
        poll_count: int = 300,
    ) -> bool:
        for _ in range(poll_count):
            active_tab = self.session_browser._active_tab(session)
            if await self.is_logged_in(active_tab):
                return True
            await self.session_browser._sleep_ms(1000)
        return False

    async def fill_login_form(
        self,
        session: CoupangBrowserSession,
        email: str,
        password: str,
    ) -> bool:
        email_input = await self.session_browser._safe_select(
            session.tab, 'input[name="email"], input#login-email-input'
        )
        password_input = await self.session_browser._safe_select(
            session.tab, 'input[name="password"], input#login-password-input'
        )
        submit_button = await self.session_browser._safe_select(
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

        await self.session_browser._sleep_ms(500)
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

    async def _read_login_state(self, tab: BrowserTab) -> LoginPageState:
        page_url = getattr(tab, "url", "")
        login_link = await self.session_browser._safe_select(tab, COUPANG_LOGIN_LINK_SELECTOR)
        my_coupang_link = await self.session_browser._safe_select(tab, COUPANG_MYCOUPANG_SELECTOR)
        return LoginPageState(
            url=str(page_url),
            has_login_link=login_link is not None,
            has_mycoupang_link=my_coupang_link is not None,
        )
