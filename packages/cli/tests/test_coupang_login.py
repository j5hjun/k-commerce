from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

sys.modules.setdefault(
    "asyncclick",
    types.SimpleNamespace(echo=lambda *args, **kwargs: None, secho=lambda *args, **kwargs: None),
)
sys.modules.setdefault("nodriver", types.SimpleNamespace(start=AsyncMock()))

from k_commerce_cli.providers.coupang.browser import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_URL,
    CoupangBrowser,
    CoupangBrowserSession,
)
from k_commerce_cli.providers.coupang.login import CoupangLoginProvider
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.coupang.session_store import CoupangSessionStore


class _DummyElement:
    def __init__(self) -> None:
        self.click = AsyncMock()
        self.send_keys = AsyncMock()


class _DummyKeyboard:
    def __init__(self) -> None:
        self.press = AsyncMock()


class _DummyTab:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.get_calls: list[str] = []
        self.select_map: dict[str, object | None] = {}
        self.select_errors: dict[str, Exception] = {}
        self.keyboard = _DummyKeyboard()
        self.evaluate_result = None
        self.evaluate_error: Exception | None = None
        self.evaluate_calls: list[str] = []

    async def get(self, url: str) -> None:
        self.get_calls.append(url)
        self.url = url
        if url == COUPANG_LOGIN_URL and getattr(self, "fail_login", False):
            raise RuntimeError("blocked")

    async def select(self, selector: str, timeout: int = 0):
        if selector in self.select_errors:
            raise self.select_errors[selector]
        return self.select_map.get(selector)

    async def evaluate(self, _script: str, *_args):
        self.evaluate_calls.append(_script)
        if self.evaluate_error is not None:
            raise self.evaluate_error
        return self.evaluate_result


class _DummyCookies:
    def __init__(self) -> None:
        self.save = AsyncMock()
        self.load = AsyncMock()


class _DummyBrowser:
    def __init__(self, tab: _DummyTab | None = None) -> None:
        self.main_tab = tab
        self.tabs = [tab] if tab is not None else []
        self.get = AsyncMock(return_value=tab)
        self.stop = AsyncMock()
        self.cookies = _DummyCookies()


class _FakeNodriverRuntime:
    def __init__(self, browser: _DummyBrowser) -> None:
        self.start = AsyncMock(return_value=browser)


class _BrowserSpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.open_login_entry = AsyncMock()
        self.open_home = AsyncMock()
        self.is_logged_in = AsyncMock()
        self.wait_for_manual_login = AsyncMock()
        self.fill_login_form = AsyncMock()
        self.save_session = AsyncMock()
        self.close = AsyncMock()


class CoupangBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_launch_uses_profile_dir_and_loads_cookies(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        runtime_browser = _DummyBrowser(tab)
        nodriver_module = sys.modules["nodriver"]
        original_start = nodriver_module.start
        start_mock = AsyncMock(return_value=runtime_browser)
        nodriver_module.start = start_mock

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                base_dir = Path(temp_dir) / ".k-commerce" / "coupang"
                base_dir.mkdir(parents=True)
                cookies_file = base_dir / "cookies.dat"
                cookies_file.write_text("cookies", encoding="utf-8")

                session = await browser.launch(base_dir)
        finally:
            nodriver_module.start = original_start

        self.assertEqual(start_mock.await_args.kwargs["user_data_dir"], str(base_dir / "chrome-profile"))
        runtime_browser.cookies.load.assert_awaited_once_with(file=str(cookies_file))
        self.assertEqual(session.profile_dir, base_dir / "chrome-profile")
        self.assertEqual(session.cookies_file, cookies_file)

    async def test_open_login_entry_opens_login_page_directly(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        session = CoupangBrowserSession(browser=_DummyBrowser(tab), tab=tab, profile_dir=Path("/tmp/profile"), cookies_file=Path("/tmp/cookies.dat"))

        await browser.open_login_entry(session)

        self.assertEqual(tab.get_calls, [COUPANG_LOGIN_URL])

    async def test_is_logged_in_checks_expected_selectors(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        tab.url = COUPANG_HOME_URL
        tab.select_map = {
            'a[href*="login/login.pang"]': None,
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': object(),
        }

        self.assertTrue(await browser.is_logged_in(tab))

    async def test_is_logged_in_ignores_logout_link_on_logged_in_home(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        tab.url = COUPANG_HOME_URL
        tab.select_map = {
            'a[href*="login.coupang.com"]': object(),
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': object(),
        }

        self.assertTrue(await browser.is_logged_in(tab))

    async def test_is_logged_in_uses_evaluate_result_when_available(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        tab.url = "about:blank"
        tab.evaluate_result = {
            "url": COUPANG_HOME_URL,
            "has_login_link": False,
            "has_mycoupang_link": True,
        }

        self.assertTrue(await browser.is_logged_in(tab))

    async def test_is_logged_in_ignores_stale_selector_errors_during_navigation(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        tab.url = COUPANG_HOME_URL
        tab.evaluate_error = RuntimeError("execution context changed")
        tab.select_map = {
            'a[href*="login.coupang.com"]': None,
        }
        tab.select_errors = {
            'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': RuntimeError("stale node"),
        }

        self.assertFalse(await browser.is_logged_in(tab))

    async def test_fill_login_form_uses_evaluate_when_available(self) -> None:
        browser = CoupangBrowser()
        tab = _DummyTab()
        tab.evaluate_result = True
        session = CoupangBrowserSession(
            browser=_DummyBrowser(tab),
            tab=tab,
            profile_dir=Path("/tmp/profile"),
            cookies_file=Path("/tmp/cookies.dat"),
        )

        result = await browser.fill_login_form(session, "user@example.com", "secret")

        self.assertTrue(result)
        self.assertTrue(any("login-email-input" in script for script in tab.evaluate_calls))

    async def test_active_tab_prefers_web_page_over_chrome_ui_tab(self) -> None:
        browser = CoupangBrowser()
        coupang_tab = _DummyTab()
        coupang_tab.url = COUPANG_HOME_URL
        chrome_ui_tab = _DummyTab()
        chrome_ui_tab.url = "chrome://omnibox-popup.top-chrome/"
        runtime_browser = _DummyBrowser(coupang_tab)
        runtime_browser.tabs = [coupang_tab, chrome_ui_tab]
        session = CoupangBrowserSession(
            browser=runtime_browser,
            tab=coupang_tab,
            profile_dir=Path("/tmp/profile"),
            cookies_file=Path("/tmp/cookies.dat"),
        )

        self.assertIs(browser._active_tab(session), coupang_tab)


class CoupangLoginProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_default_credentials_path_uses_session_store_location(self) -> None:
        provider = CoupangLoginProvider()

        self.assertEqual(
            provider.credentials_path,
            provider.paths.credentials_path,
        )
        self.assertEqual(
            provider.paths.base_dir,
            Path.home() / ".k-commerce" / "coupang",
        )
        self.assertEqual(provider.session_store.paths, provider.credential_store.paths)

    async def test_restore_session_uses_profile_dir_when_present(self) -> None:
        provider = CoupangLoginProvider()
        browser = _BrowserSpy()
        provider.browser = browser
        with tempfile.TemporaryDirectory() as temp_dir:
            provider.session_store = CoupangSessionStore(provider="coupang", root_dir=Path(temp_dir))
            provider.paths = provider.session_store.paths
            provider.session_store.profile_dir.mkdir(parents=True)
            await provider._restore_session()

        browser.launch.assert_awaited_once_with(provider.session_store.base_dir)

    async def test_login_with_credentials_uses_browser_form_submission(self) -> None:
        provider = CoupangLoginProvider()
        browser = _BrowserSpy()
        session = object()
        browser.launch = AsyncMock(return_value=session)
        browser.fill_login_form = AsyncMock(return_value=True)
        browser.wait_for_manual_login = AsyncMock(return_value=True)
        provider.browser = browser

        result = await provider._login_with_credentials(
            type("Creds", (), {"email": "user@example.com", "password": "secret"})()
        )

        self.assertTrue(result)
        browser.open_login_entry.assert_awaited_once_with(session)
        browser.fill_login_form.assert_awaited_once_with(session, "user@example.com", "secret")

    async def test_persist_session_saves_cookies_and_metadata(self) -> None:
        provider = CoupangLoginProvider()
        browser = _BrowserSpy()
        session = object()
        provider.browser = browser
        provider._browser_session = session
        with tempfile.TemporaryDirectory() as temp_dir:
            provider.session_store = CoupangSessionStore(provider="coupang", root_dir=Path(temp_dir))
            provider.paths = provider.session_store.paths
            await provider._persist_session("automatic")
            metadata = provider.session_store.session_meta_path.read_text(encoding="utf-8")

        browser.save_session.assert_awaited_once_with(session)
        self.assertIn('"login_method": "automatic"', metadata)

    async def test_wait_for_manual_login_delegates_to_browser(self) -> None:
        provider = CoupangLoginProvider()
        browser = _BrowserSpy()
        session = object()
        provider.browser = browser
        provider._browser_session = session
        browser.wait_for_manual_login = AsyncMock(return_value=True)

        self.assertTrue(await provider._wait_for_manual_login())
        browser.wait_for_manual_login.assert_awaited_once_with(session)

    async def test_close_browser_session_handles_non_awaitable_stop(self) -> None:
        provider = CoupangLoginProvider()
        session = CoupangBrowserSession(
            browser=types.SimpleNamespace(stop=lambda: None),
            tab=_DummyTab(),
            profile_dir=Path("/tmp/profile"),
            cookies_file=Path("/tmp/cookies.dat"),
        )
        provider._browser_session = session

        await provider._close_browser_session()

        self.assertIsNone(provider._browser_session)


if __name__ == "__main__":
    unittest.main()
