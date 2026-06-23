from __future__ import annotations

import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock

_fake_click = types.SimpleNamespace(echo=lambda *args, **kwargs: None, secho=lambda *args, **kwargs: None)
sys.modules.setdefault("asyncclick", _fake_click)

_fake_playwright_async_api = types.SimpleNamespace(
    Error=RuntimeError,
    TimeoutError=TimeoutError,
    async_playwright=AsyncMock(),
)
sys.modules.setdefault("playwright", types.SimpleNamespace(async_api=_fake_playwright_async_api))
sys.modules.setdefault("playwright.async_api", _fake_playwright_async_api)

from k_commerce_cli.providers.coupang.browser import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_URL,
    CoupangBrowser,
    CoupangBrowserSession,
)
from k_commerce_cli.providers.coupang.login import CoupangLoginProvider


class _DummyPage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.goto_calls: list[tuple[str, dict[str, object]]] = []
        self.click_calls: list[str] = []
        self.query_selector_map: dict[str, object | None] = {}
        self.wait_for_timeout_calls: list[int] = []
        self.fill_calls: list[tuple[str, str]] = []
        self.keyboard_presses: list[str] = []
        self.closed = False
        self.fail_login_goto = False
        self.keyboard = SimpleNamespace(press=self._keyboard_press)

    async def goto(self, url: str, **kwargs: object) -> None:
        self.goto_calls.append((url, kwargs))
        self.url = url
        if self.fail_login_goto and url == COUPANG_LOGIN_URL:
            raise RuntimeError("login url blocked")

    async def click(self, selector: str) -> None:
        self.click_calls.append(selector)

    async def query_selector(self, selector: str) -> object | None:
        return self.query_selector_map.get(selector)

    async def fill(self, selector: str, value: str) -> None:
        self.fill_calls.append((selector, value))

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_for_timeout_calls.append(timeout_ms)

    async def _keyboard_press(self, key: str) -> None:
        self.keyboard_presses.append(key)

    def is_closed(self) -> bool:
        return self.closed


class _DummyElement:
    def __init__(self, page: _DummyPage, selector: str) -> None:
        self.page = page
        self.selector = selector

    async def click(self) -> None:
        self.page.click_calls.append(self.selector)

    async def fill(self, value: str) -> None:
        self.page.fill_calls.append((self.selector, value))


class _DummyContext:
    def __init__(self, pages: list[_DummyPage] | None = None) -> None:
        self.pages = pages or []


class _BrowserEntrySpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.open_login_entry = AsyncMock()
        self.wait_for_manual_login = AsyncMock()
        self.is_logged_in = AsyncMock()
        self.save_storage_state = AsyncMock()


class _LoginCompletionBrowserSpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.open_login_entry = AsyncMock()
        self.wait_for_manual_login = AsyncMock(return_value=True)


class _FakeStorageContext:
    def __init__(self) -> None:
        self.storage_state = AsyncMock()


class CoupangBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_login_entry_falls_back_to_home_then_product(self) -> None:
        browser = CoupangBrowser()
        browser.random_delay = AsyncMock()
        page = _DummyPage()
        page.fail_login_goto = True
        page.query_selector_map = {
            'input#query, input[name="query"]': _DummyElement(page, 'input#query, input[name="query"]'),
            'a[href*="coupang.com"]': _DummyElement(page, 'a[href*="coupang.com"]'),
        }
        session = CoupangBrowserSession(
            playwright=object(),
            browser=object(),
            context=_DummyContext([page]),
            page=page,
        )

        await browser.open_login_entry(session)

        self.assertEqual(
            page.goto_calls,
            [
                ("https://www.naver.com/", {"wait_until": "domcontentloaded"}),
                (
                    COUPANG_LOGIN_URL,
                    {
                        "wait_until": "domcontentloaded",
                        "referer": COUPANG_HOME_URL,
                    },
                ),
                (COUPANG_HOME_URL, {"wait_until": "domcontentloaded"}),
            ],
        )
        self.assertEqual(page.fill_calls, [('input#query, input[name="query"]', "쿠팡")])
        self.assertEqual(page.keyboard_presses, ["Enter"])
        self.assertEqual(
            page.click_calls,
            ['input#query, input[name="query"]', 'a[href*="coupang.com"]', 'a[href^="/vp/products/"]'],
        )

    async def test_select_active_page_returns_last_open_page(self) -> None:
        browser = CoupangBrowser()
        closed_page = _DummyPage()
        closed_page.closed = True
        open_page = _DummyPage()
        session = CoupangBrowserSession(
            playwright=object(),
            browser=object(),
            context=_DummyContext([closed_page, open_page]),
            page=closed_page,
        )

        selected = browser.select_active_page(session, closed_page)

        self.assertIs(selected, open_page)

    async def test_is_logged_in_returns_true_when_my_coupang_visible_and_login_hidden(self) -> None:
        browser = CoupangBrowser()
        page = _DummyPage()
        page.url = COUPANG_HOME_URL
        page.query_selector_map = {
            'a[href*="login.coupang.com"]': None,
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': object(),
        }

        result = await browser.is_logged_in(page)

        self.assertTrue(result)


class CoupangLoginProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_with_credentials_uses_browser_open_login_entry(self) -> None:
        provider = CoupangLoginProvider()
        browser = _BrowserEntrySpy()
        page = AsyncMock()
        session = type("Session", (), {"page": page})()
        provider.browser = browser
        provider._browser_session = session

        page.wait_for_url = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        provider._current_page_is_logged_in = AsyncMock(return_value=True)

        result = await provider._login_with_credentials(
            type("Creds", (), {"email": "user@example.com", "password": "secret"})()
        )

        self.assertTrue(result)
        browser.open_login_entry.assert_awaited_once_with(session)

    async def test_persist_session_writes_storage_state_and_metadata(self) -> None:
        provider = CoupangLoginProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            provider.credentials_path = Path(temp_dir) / "credentials.json"
            context = _FakeStorageContext()
            provider._browser_session = type("Session", (), {"context": context})()

            await provider._persist_session("automatic")

            context.storage_state.assert_awaited_once_with(
                path=provider.session_store.storage_state_path
            )
            metadata = provider.session_store.session_meta_path.read_text(encoding="utf-8")
            self.assertIn('"login_method": "automatic"', metadata)

    async def test_wait_for_manual_login_delegates_to_browser(self) -> None:
        provider = CoupangLoginProvider()
        browser = _LoginCompletionBrowserSpy()
        page = AsyncMock()
        session = type("Session", (), {"page": page})()
        provider.browser = browser
        provider._browser_session = session

        result = await provider._wait_for_manual_login()

        self.assertTrue(result)
        browser.wait_for_manual_login.assert_awaited_once_with(session)

    def test_default_credentials_path_matches_ts_session_dir(self) -> None:
        provider = CoupangLoginProvider()

        self.assertEqual(provider.credentials_path.name, "credentials.json")
        self.assertEqual(provider.credentials_path.parent.name, ".coupang-session")


if __name__ == "__main__":
    unittest.main()
