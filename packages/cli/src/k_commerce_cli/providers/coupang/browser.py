from __future__ import annotations

import asyncio
import inspect
import random
from dataclasses import dataclass
from pathlib import Path

import nodriver as uc

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
COUPANG_VIEWPORT = {"width": 1440, "height": 900}
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = (
    'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
)
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class CoupangBrowserSession:
    browser: object
    tab: object
    profile_dir: Path
    cookies_file: Path


class CoupangBrowser:
    async def launch(self, base_dir: Path) -> CoupangBrowserSession:
        profile_dir = self.profile_dir(base_dir)
        cookies_file = self.cookies_file(base_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

        browser = await uc.start(
            headless=False,
            user_data_dir=str(profile_dir),
            browser_args=[
                f"--window-size={COUPANG_VIEWPORT['width']},{COUPANG_VIEWPORT['height']}",
                "--lang=ko-KR",
            ],
            lang="ko-KR",
        )
        tab = await self._ensure_tab(browser)
        await self._load_cookies(browser, cookies_file)
        return CoupangBrowserSession(
            browser=browser,
            tab=tab,
            profile_dir=profile_dir,
            cookies_file=cookies_file,
        )

    async def open_home(self, session: CoupangBrowserSession) -> None:
        await session.tab.get(COUPANG_HOME_URL)

    async def open_login(self, session: CoupangBrowserSession) -> None:
        await session.tab.get(COUPANG_LOGIN_URL)

    async def open_login_entry(self, session: CoupangBrowserSession) -> None:
        await self.open_login(session)

    async def is_logged_in(self, tab: object) -> bool:
        page_state = await self._read_login_state(tab)
        page_url = page_state["url"]
        if "login.coupang.com" in page_url:
            return False

        return (not page_state["has_login_link"]) and page_state["has_mycoupang_link"]

    async def wait_for_manual_login(
        self,
        session: CoupangBrowserSession,
        poll_count: int = 300,
    ) -> bool:
        for _ in range(poll_count):
            active_tab = self._active_tab(session)
            if await self.is_logged_in(active_tab):
                return True
            await self._sleep_ms(1000)
        return False

    async def save_session(self, session: CoupangBrowserSession) -> None:
        cookies_api = getattr(session.browser, "cookies", None)
        save = getattr(cookies_api, "save", None)
        if save is not None:
            await save(file=str(session.cookies_file))

    async def close(self, session: CoupangBrowserSession) -> None:
        stop = getattr(session.browser, "stop", None)
        if stop is not None:
            result = stop()
            if inspect.isawaitable(result):
                await result
        await asyncio.sleep(1.0)

    def profile_dir(self, base_dir: Path) -> Path:
        return base_dir / "chrome-profile"

    def cookies_file(self, base_dir: Path) -> Path:
        return base_dir / "cookies.dat"

    async def fill_login_form(
        self,
        session: CoupangBrowserSession,
        email: str,
        password: str,
    ) -> bool:
        evaluate = getattr(session.tab, "evaluate", None)
        if callable(evaluate):
            try:
                result = await evaluate(
                    """
                    ([email, password]) => {
                      const emailInput = document.querySelector('input[name="email"], input#login-email-input');
                      const passwordInput = document.querySelector('input[name="password"], input#login-password-input');
                      const submitButton = document.querySelector('button[type="submit"], .login__button');
                      if (!emailInput || !passwordInput || !submitButton) return false;
                      emailInput.focus();
                      emailInput.value = email;
                      emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                      emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                      passwordInput.focus();
                      passwordInput.value = password;
                      passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                      passwordInput.dispatchEvent(new Event('change', { bubbles: true }));
                      submitButton.click();
                      return true;
                    }
                    """,
                    [email, password],
                )
                if isinstance(result, bool):
                    return result
            except Exception:
                pass

        email_input = await self._safe_select(session.tab, 'input[name="email"], input#login-email-input')
        password_input = await self._safe_select(session.tab, 'input[name="password"], input#login-password-input')
        submit_button = await self._safe_select(session.tab, 'button[type="submit"], .login__button')

        if email_input is None or password_input is None or submit_button is None:
            return False

        await email_input.send_keys(email)
        await password_input.send_keys(password)
        await submit_button.click()
        return True

    async def random_delay(self, min_ms: int = 500, max_ms: int = 2_000) -> None:
        await self._sleep_ms(random.randint(min_ms, max_ms))

    async def _sleep_ms(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)

    async def _ensure_tab(self, browser: object) -> object:
        main_tab = getattr(browser, "main_tab", None)
        if main_tab is not None:
            return main_tab
        return await browser.get("about:blank")

    async def _load_cookies(self, browser: object, cookies_file: Path) -> None:
        if not cookies_file.is_file():
            return

        cookies_api = getattr(browser, "cookies", None)
        load = getattr(cookies_api, "load", None)
        if load is not None:
            await load(file=str(cookies_file))

    async def _safe_select(self, tab: object, selector: str, timeout: int = 1):
        try:
            return await tab.select(selector, timeout=timeout)
        except Exception:
            await self._sleep_ms(250)
            try:
                return await tab.select(selector, timeout=timeout)
            except Exception:
                return None

    def _active_tab(self, session: CoupangBrowserSession) -> object:
        tabs = getattr(session.browser, "tabs", None)
        candidates: list[object] = []
        if isinstance(tabs, list):
            candidates.extend(reversed(tabs))

        main_tab = getattr(session.browser, "main_tab", None)
        if main_tab is not None:
            candidates.append(main_tab)
        candidates.append(session.tab)

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if "coupang.com" in url:
                return candidate

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if url.startswith(("https://", "http://", "about:blank")):
                return candidate

        for candidate in candidates:
            if hasattr(candidate, "select"):
                return candidate

        return session.tab

    async def _read_login_state(self, tab: object) -> dict[str, object]:
        evaluate = getattr(tab, "evaluate", None)
        if callable(evaluate):
            try:
                result = await evaluate(
                    """
                    (() => ({
                      url: window.location.href,
                      has_login_link: document.querySelector('a[href*="login/login.pang"]') !== null,
                      has_mycoupang_link:
                        document.querySelector('a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]') !== null
                    }))()
                    """
                )
                if isinstance(result, dict):
                    return {
                        "url": str(result.get("url", "")),
                        "has_login_link": bool(result.get("has_login_link", False)),
                        "has_mycoupang_link": bool(result.get("has_mycoupang_link", False)),
                    }
            except Exception:
                pass

        page_url = getattr(tab, "url", "")
        login_link = await self._safe_select(tab, COUPANG_LOGIN_LINK_SELECTOR)
        my_coupang_link = await self._safe_select(tab, COUPANG_MYCOUPANG_SELECTOR)
        return {
            "url": page_url,
            "has_login_link": login_link is not None,
            "has_mycoupang_link": my_coupang_link is not None,
        }
