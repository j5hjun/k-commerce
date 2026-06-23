import unittest
from unittest.mock import AsyncMock, patch

from k_commerce_cli.providers.coupang.browser import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_URL,
    COUPANG_USER_AGENT,
    COUPANG_VIEWPORT,
    CoupangBrowser,
    CoupangBrowserSession,
    first_product_link_selector,
)


class CoupangBrowserModuleTests(unittest.TestCase):
    def test_constants_match_expected_entrypoints(self) -> None:
        self.assertEqual(COUPANG_HOME_URL, "https://www.coupang.com/")
        self.assertEqual(COUPANG_LOGIN_URL, "https://login.coupang.com/login/login.pang")

    def test_product_link_selector_targets_product_pages(self) -> None:
        self.assertEqual(first_product_link_selector(), 'a[href^="/vp/products/"]')


class CoupangBrowserLaunchTests(unittest.IsolatedAsyncioTestCase):
    async def test_launch_uses_firefox_first_with_expected_context_settings(self) -> None:
        page = object()
        context = AsyncMock()
        context.new_page.return_value = page
        browser = AsyncMock()
        browser.new_context.return_value = context
        firefox = AsyncMock()
        firefox.launch.return_value = browser
        chromium = AsyncMock()
        playwright = AsyncMock()
        playwright.firefox = firefox
        playwright.chromium = chromium
        async_playwright = AsyncMock()
        async_playwright.start.return_value = playwright

        with patch(
            "k_commerce_cli.providers.coupang.browser.async_playwright",
            return_value=async_playwright,
        ):
            session = await CoupangBrowser().launch()

        self.assertIsInstance(session, CoupangBrowserSession)
        firefox.launch.assert_awaited_once_with(headless=False)
        browser.new_context.assert_awaited_once_with(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport=COUPANG_VIEWPORT,
            user_agent=COUPANG_USER_AGENT,
        )
        self.assertIs(session.page, page)

    async def test_launch_falls_back_to_chrome_when_firefox_launch_fails(self) -> None:
        context = AsyncMock()
        context.new_page.return_value = object()
        browser = AsyncMock()
        browser.new_context.return_value = context
        firefox = AsyncMock()
        firefox.launch.side_effect = RuntimeError("firefox failed")
        chromium = AsyncMock()
        chromium.launch.return_value = browser
        playwright = AsyncMock()
        playwright.firefox = firefox
        playwright.chromium = chromium
        async_playwright = AsyncMock()
        async_playwright.start.return_value = playwright

        with patch(
            "k_commerce_cli.providers.coupang.browser.async_playwright",
            return_value=async_playwright,
        ):
            session = await CoupangBrowser().launch()

        chromium.launch.assert_awaited_once_with(headless=False)
        self.assertIsInstance(session, CoupangBrowserSession)
