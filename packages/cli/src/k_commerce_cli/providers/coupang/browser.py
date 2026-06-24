from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
NAVER_HOME_URL = "https://www.naver.com/"
COUPANG_VIEWPORT = {"width": 1440, "height": 900}
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
FIREFOX_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) "
    "Gecko/20100101 Firefox/146.0"
)


@dataclass(frozen=True)
class CoupangBrowserSession:
    playwright: object
    browser: object | None
    context: object
    page: object
    persistent: bool = False


def first_product_link_selector() -> str:
    return 'a[href^="/vp/products/"]'


class CoupangBrowser:
    async def launch(
        self,
        preferred: Literal["firefox", "chrome"] | None = None,
        storage_state_path: Path | None = None,
        base_dir: Path | None = None,
    ) -> CoupangBrowserSession:
        playwright = await async_playwright().start()
        if preferred is None:
            preferred = self._default_browser()
        if preferred == "chrome":
            return await self._launch_chrome_persistent(playwright, base_dir=base_dir)
        return await self._launch_firefox(
            playwright,
            storage_state_path=storage_state_path,
        )

    async def open_home(self, session: CoupangBrowserSession) -> None:
        await session.page.goto(COUPANG_HOME_URL, wait_until="domcontentloaded")

    async def open_login(self, session: CoupangBrowserSession) -> None:
        await session.page.goto(
            COUPANG_LOGIN_URL,
            wait_until="domcontentloaded",
            referer=COUPANG_HOME_URL,
        )

    async def open_login_entry(self, session: CoupangBrowserSession) -> None:
        try:
            await self._open_via_naver(session)
            await self.open_login(session)
        except Exception:
            await self.open_home(session)
            await session.page.click(first_product_link_selector())

    def select_active_page(
        self,
        session: CoupangBrowserSession,
        current_page: object,
    ) -> object:
        is_closed = getattr(current_page, "is_closed", None)
        if callable(is_closed) and not is_closed():
            return current_page

        for candidate in reversed(session.context.pages):
            candidate_is_closed = getattr(candidate, "is_closed", None)
            if callable(candidate_is_closed) and not candidate_is_closed():
                return candidate

        return current_page

    async def wait_for_manual_login(
        self,
        session: CoupangBrowserSession,
        timeout_ms: int = 300_000,
        poll_count: int = 300,
    ) -> bool:
        page = session.page

        if "login.coupang.com" in page.url:
            try:
                await page.wait_for_url(
                    lambda url: "login.coupang.com" not in str(url),
                    timeout=timeout_ms,
                )
            except PlaywrightTimeoutError:
                return False

        for _ in range(poll_count):
            page = self.select_active_page(session, page)
            if await self.is_logged_in(page):
                return True
            try:
                await page.wait_for_timeout(1000)
            except PlaywrightError:
                page = self.select_active_page(session, page)

        return False

    async def is_logged_in(self, page: object) -> bool:
        page_url = getattr(page, "url", "")
        if "login.coupang.com" in page_url:
            return False

        login_link = await page.query_selector('a[href*="login.coupang.com"]')
        my_coupang_link = await page.query_selector(
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
        )
        return login_link is None and my_coupang_link is not None

    async def save_storage_state(
        self,
        session: CoupangBrowserSession,
        storage_state_path: Path,
    ) -> None:
        if getattr(session, "persistent", False):
            return
        await session.context.storage_state(path=storage_state_path)

    async def close(self, session: CoupangBrowserSession) -> None:
        try:
            await session.page.close()
        finally:
            try:
                await session.context.close()
            finally:
                try:
                    if session.browser is not None:
                        await session.browser.close()
                finally:
                    stop = getattr(session.playwright, "stop", None)
                    if stop is not None:
                        await stop()

    async def random_delay(self, min_ms: int = 500, max_ms: int = 2_000) -> None:
        await self._sleep_ms(random.randint(min_ms, max_ms))

    async def _sleep_ms(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)

    async def _open_via_naver(self, session: CoupangBrowserSession) -> None:
        page = session.page
        await page.goto(NAVER_HOME_URL, wait_until="domcontentloaded")
        await self.random_delay(1_000, 2_000)
        search_input = await page.query_selector('input#query, input[name="query"]')
        if search_input is None:
            return

        await page.click('input#query, input[name="query"]')
        await self.random_delay(300, 600)
        await page.fill('input#query, input[name="query"]', "쿠팡")
        await self.random_delay(300, 500)
        await page.keyboard.press("Enter")
        await self.random_delay(2_000, 3_000)

        coupang_link = await page.query_selector('a[href*="coupang.com"]')
        if coupang_link is not None:
            await page.click('a[href*="coupang.com"]')
            await self.random_delay(2_000, 3_000)

    def _default_browser(self) -> Literal["firefox", "chrome"]:
        return "chrome" if os.getenv("COUPANG_BROWSER") == "chrome" else "firefox"

    def chrome_profile_dir(self, base_dir: Path | None = None) -> Path:
        root_dir = base_dir or (Path.home() / ".k-commerce" / "coupang")
        return root_dir / "chrome-profile"

    async def _launch_firefox(
        self,
        playwright: object,
        storage_state_path: Path | None = None,
    ) -> CoupangBrowserSession:
        browser = await playwright.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "general.useragent.override": "",
                "intl.accept_languages": "ko-KR,ko,en-US,en",
                "privacy.resistFingerprinting": False,
            },
        )
        context_kwargs = dict(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport=COUPANG_VIEWPORT,
            user_agent=FIREFOX_USER_AGENT,
        )
        if storage_state_path is not None:
            context_kwargs["storage_state"] = storage_state_path
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        return CoupangBrowserSession(
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
        )

    async def _launch_chrome_persistent(
        self,
        playwright: object,
        base_dir: Path | None = None,
    ) -> CoupangBrowserSession:
        profile_dir = self.chrome_profile_dir(base_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = await playwright.chromium.launch_persistent_context(
            profile_dir,
            channel="chrome",
            headless=False,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport=COUPANG_VIEWPORT,
            user_agent=CHROME_USER_AGENT,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        return CoupangBrowserSession(
            playwright=playwright,
            browser=None,
            context=context,
            page=page,
            persistent=True,
        )
