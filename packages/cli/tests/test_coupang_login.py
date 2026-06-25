from __future__ import annotations

# ruff: noqa: E402

import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.modules.setdefault("nodriver", types.SimpleNamespace(start=AsyncMock()))

from k_commerce_cli.providers.coupang.browser import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_URL,
    CoupangBrowser,
    CoupangBrowserSession,
)
from k_commerce_cli.providers.coupang.login import CoupangLoginProvider
from k_commerce_cli.providers.coupang.status import CoupangStatusProvider
from k_commerce_cli.providers.coupang.session_store import CoupangSessionStore
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.types import StatusResult


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


@pytest.mark.anyio
async def test_launch_uses_profile_dir_and_loads_cookies() -> None:
    browser = CoupangBrowser()
    tab = _DummyTab()
    runtime_browser = _DummyBrowser(tab)
    nodriver_module = sys.modules["nodriver"]
    original_start = nodriver_module.start
    start_mock = AsyncMock(return_value=runtime_browser)
    nodriver_module.start = start_mock

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = ProviderPaths("coupang", root_dir=Path(temp_dir) / ".k-commerce")
            paths.base_dir.mkdir(parents=True)
            cookies_file = paths.cookies_file
            cookies_file.write_text("cookies", encoding="utf-8")

            session = await browser.launch(paths)
    finally:
        nodriver_module.start = original_start

    assert start_mock.await_args.kwargs["user_data_dir"] == str(paths.profile_dir)
    runtime_browser.cookies.load.assert_awaited_once_with(file=str(cookies_file))
    assert session.profile_dir == paths.profile_dir
    assert session.cookies_file == cookies_file


@pytest.mark.anyio
async def test_open_login_entry_opens_login_page_directly() -> None:
    browser = CoupangBrowser()
    tab = _DummyTab()
    session = CoupangBrowserSession(
        browser=_DummyBrowser(tab),
        tab=tab,
        profile_dir=Path("/tmp/profile"),
        cookies_file=Path("/tmp/cookies.dat"),
    )

    await browser.open_login_entry(session)

    assert tab.get_calls == [COUPANG_LOGIN_URL]


@pytest.mark.anyio
async def test_is_logged_in_checks_expected_selectors() -> None:
    browser = CoupangBrowser()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.select_map = {
        'a[href*="login/login.pang"]': None,
        'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': object(),
    }

    assert await browser.is_logged_in(tab) is True


@pytest.mark.anyio
async def test_is_logged_in_ignores_logout_link_on_logged_in_home() -> None:
    browser = CoupangBrowser()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.select_map = {
        'a[href*="login.coupang.com"]': object(),
        'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]': object(),
    }

    assert await browser.is_logged_in(tab) is True


@pytest.mark.anyio
async def test_is_logged_in_uses_evaluate_result_when_available() -> None:
    browser = CoupangBrowser()
    tab = _DummyTab()
    tab.url = "about:blank"
    tab.evaluate_result = {
        "url": COUPANG_HOME_URL,
        "has_login_link": False,
        "has_mycoupang_link": True,
    }

    assert await browser.is_logged_in(tab) is True


@pytest.mark.anyio
async def test_is_logged_in_ignores_stale_selector_errors_during_navigation() -> None:
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

    assert await browser.is_logged_in(tab) is False


@pytest.mark.anyio
async def test_fill_login_form_uses_evaluate_when_available() -> None:
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

    assert result is True
    assert any("login-email-input" in script for script in tab.evaluate_calls)


@pytest.mark.anyio
async def test_active_tab_prefers_web_page_over_chrome_ui_tab() -> None:
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

    assert browser._active_tab(session) is coupang_tab


def test_default_credentials_path_uses_session_store_location() -> None:
    provider = CoupangLoginProvider()

    assert provider.credential_store.credentials_path == provider.session_store.paths.credentials_path
    assert provider.session_store.paths.base_dir == Path.home() / ".k-commerce" / "coupang"
    assert provider.session_store.paths == provider.credential_store.paths


def test_configure_paths_uses_overridden_root_dir(tmp_path: Path) -> None:
    provider = CoupangLoginProvider()

    provider._configure_paths(tmp_path)

    assert provider.session_store.paths.base_dir == tmp_path / "coupang"
    assert provider.credential_store.credentials_path == tmp_path / "coupang" / "credentials.json"
    assert provider.session_store.base_dir == tmp_path / "coupang"


@pytest.mark.anyio
async def test_restore_session_uses_profile_dir_when_present() -> None:
    provider = CoupangLoginProvider()
    browser = _BrowserSpy()
    provider.browser = browser
    with tempfile.TemporaryDirectory() as temp_dir:
        provider.session_store = CoupangSessionStore(provider="coupang", root_dir=Path(temp_dir))
        provider.session_store.profile_dir.mkdir(parents=True)
        await provider._restore_session()

    browser.launch.assert_awaited_once_with(provider.session_store.paths)


@pytest.mark.anyio
async def test_login_with_credentials_uses_browser_form_submission() -> None:
    provider = CoupangLoginProvider()
    browser = _BrowserSpy()
    session = object()
    browser.launch = AsyncMock(return_value=session)
    browser.fill_login_form = AsyncMock(return_value=True)
    browser.wait_for_manual_login = AsyncMock(return_value=True)
    provider.browser = browser

    result = await provider._login_with_credentials(type("Creds", (), {"email": "user@example.com", "password": "secret"})())

    assert result is True
    browser.open_login_entry.assert_awaited_once_with(session)
    browser.fill_login_form.assert_awaited_once_with(session, "user@example.com", "secret")


@pytest.mark.anyio
async def test_persist_session_saves_cookies_and_metadata() -> None:
    provider = CoupangLoginProvider()
    browser = _BrowserSpy()
    session = object()
    provider.browser = browser
    provider._browser_session = session
    with tempfile.TemporaryDirectory() as temp_dir:
        provider.session_store = CoupangSessionStore(provider="coupang", root_dir=Path(temp_dir))
        await provider._persist_session("automatic")
        metadata = provider.session_store.session_meta_path.read_text(encoding="utf-8")

    browser.save_session.assert_awaited_once_with(session)
    assert '"login_method": "automatic"' in metadata


@pytest.mark.anyio
async def test_wait_for_manual_login_delegates_to_browser() -> None:
    provider = CoupangLoginProvider()
    browser = _BrowserSpy()
    session = object()
    provider.browser = browser
    provider._browser_session = session
    browser.wait_for_manual_login = AsyncMock(return_value=True)

    assert await provider._wait_for_manual_login() is True
    browser.wait_for_manual_login.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_close_browser_session_handles_non_awaitable_stop() -> None:
    provider = CoupangLoginProvider()
    session = CoupangBrowserSession(
        browser=types.SimpleNamespace(stop=lambda: None),
        tab=_DummyTab(),
        profile_dir=Path("/tmp/profile"),
        cookies_file=Path("/tmp/cookies.dat"),
    )
    provider._browser_session = session

    await provider._close_browser_session()

    assert provider._browser_session is None


@pytest.mark.anyio
async def test_login_status_opens_home_checks_state_and_closes_browser_session(
    tmp_path: Path,
) -> None:
    provider = CoupangStatusProvider()
    browser = _BrowserSpy()
    session = types.SimpleNamespace(tab=object())
    browser.launch = AsyncMock(return_value=session)
    browser.is_logged_in = AsyncMock(return_value=True)
    provider.browser = browser
    (tmp_path / "coupang" / "chrome-profile").mkdir(parents=True)

    result = await provider.status(root_dir=tmp_path)

    assert result == StatusResult(
        provider="coupang",
        logged_in=True,
        message="쿠팡 로그인 상태입니다",
    )
    browser.launch.assert_awaited_once_with(provider.session_store.paths)
    browser.open_home.assert_awaited_once_with(session)
    browser.is_logged_in.assert_awaited_once_with(session.tab)
    browser.close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_login_status_closes_browser_session_when_home_check_fails(
    tmp_path: Path,
) -> None:
    provider = CoupangStatusProvider()
    browser = _BrowserSpy()
    session = types.SimpleNamespace(tab=object())
    browser.launch = AsyncMock(return_value=session)
    browser.open_home = AsyncMock(side_effect=RuntimeError("boom"))
    provider.browser = browser
    (tmp_path / "coupang" / "chrome-profile").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="boom"):
        await provider.status(root_dir=tmp_path)

    browser.close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_login_status_returns_logged_out_without_launch_on_clean_root(
    tmp_path: Path,
) -> None:
    provider = CoupangStatusProvider()
    browser = _BrowserSpy()
    provider.browser = browser

    result = await provider.status(root_dir=tmp_path)

    assert result == StatusResult(
        provider="coupang",
        logged_in=False,
        message="쿠팡 로그인 상태가 아닙니다",
    )
    browser.launch.assert_not_awaited()
    browser.close.assert_not_awaited()
    assert provider.session_store.base_dir == tmp_path / "coupang"
    assert not provider.session_store.base_dir.exists()
