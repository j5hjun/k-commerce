from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from playwright.async_api import async_playwright

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"
COUPANG_VIEWPORT = {"width": 1440, "height": 900}
COUPANG_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class CoupangBrowserSession:
    playwright: object
    browser: object
    context: object
    page: object


def first_product_link_selector() -> str:
    return 'a[href^="/vp/products/"]'


class CoupangBrowser:
    async def launch(
        self,
        preferred: Literal["firefox", "chrome"] = "firefox",
        storage_state_path: Path | None = None,
    ) -> CoupangBrowserSession:
        playwright = await async_playwright().start()
        browser_types = (
            [playwright.firefox, playwright.chromium]
            if preferred == "firefox"
            else [playwright.chromium]
        )

        last_error: Exception | None = None

        for browser_type in browser_types:
            try:
                browser = await browser_type.launch(headless=False)
                context_kwargs = dict(
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                    viewport=COUPANG_VIEWPORT,
                    user_agent=COUPANG_USER_AGENT,
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
            except Exception as exc:
                last_error = exc

        assert last_error is not None
        raise last_error
