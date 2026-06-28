from __future__ import annotations

# ruff: noqa: E402

import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.modules.setdefault("nodriver", types.SimpleNamespace(start=AsyncMock()))

from k_commerce_cli.services.browser.nodriver import NodriverBrowser, NodriverBrowserSession
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.providers.coupang.auth import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_URL,
    COUPANG_LOGIN_LINK_SELECTOR,
    COUPANG_MYCOUPANG_SELECTOR,
    CoupangAuthService,
)
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types.auth import LoginResult, StatusResult


class _DummyElement:
    def __init__(self) -> None:
        self.text_all = ""
        self.children: list[_DummyElement] = []
        self.click = AsyncMock()
        self.send_keys = AsyncMock()

    async def query_selector_all(self, _selector: str) -> list["_DummyElement"]:
        return self.children


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
        self.save_session = AsyncMock()
        self.close = AsyncMock()
        self.select = AsyncMock()


def _make_auth_provider():
    browser = NodriverBrowser()
    store = ProviderStore(ProviderPaths("coupang"))
    return CoupangAuthService(
        provider_name="coupang",
        store=store,
        browser=browser,
    )


@pytest.mark.anyio
async def test_launch_uses_profile_dir_and_loads_cookies() -> None:
    browser = NodriverBrowser()
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


@pytest.mark.anyio
async def test_open_login_entry_opens_login_page_directly() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    session = NodriverBrowserSession(browser=_DummyBrowser(tab), tab=tab)

    await provider._open_login_entry(session)

    assert tab.get_calls == [COUPANG_LOGIN_URL]


@pytest.mark.anyio
async def test_is_logged_in_checks_expected_selectors() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.select_map = {
        COUPANG_LOGIN_LINK_SELECTOR: None,
        COUPANG_MYCOUPANG_SELECTOR: object(),
    }

    assert await provider._is_logged_in(tab) is True


@pytest.mark.anyio
async def test_is_logged_in_ignores_logout_link_on_logged_in_home() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.select_map = {
        'a[href*="login.coupang.com"]': object(),
        COUPANG_MYCOUPANG_SELECTOR: object(),
    }

    assert await provider._is_logged_in(tab) is True


@pytest.mark.anyio
async def test_is_logged_in_prefers_selectors_even_when_evaluate_exists() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.select_map = {
        COUPANG_LOGIN_LINK_SELECTOR: None,
        COUPANG_MYCOUPANG_SELECTOR: object(),
    }

    assert await provider._is_logged_in(tab) is True
    assert tab.evaluate_calls == []


@pytest.mark.anyio
async def test_is_logged_in_ignores_stale_selector_errors_during_navigation() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    tab.url = COUPANG_HOME_URL
    tab.evaluate_error = RuntimeError("execution context changed")
    tab.select_map = {
        'a[href*="login.coupang.com"]': None,
    }
    tab.select_errors = {
        COUPANG_MYCOUPANG_SELECTOR: RuntimeError("stale node"),
    }

    assert await provider._is_logged_in(tab) is False


@pytest.mark.anyio
async def test_fill_login_form_submits_after_filling_credentials() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    email_input = _DummyElement()
    password_input = _DummyElement()
    submit_button = _DummyElement()
    tab.select_map = {
        'input[name="email"], input#login-email-input': email_input,
        'input[name="password"], input#login-password-input': password_input,
        'button[type="submit"], .login__button': submit_button,
    }
    session = NodriverBrowserSession(
        browser=_DummyBrowser(tab),
        tab=tab,
    )

    result = await provider._fill_login_form(session, "user@example.com", "secret")

    assert result is True
    email_input.send_keys.assert_awaited_once_with("user@example.com")
    password_input.send_keys.assert_awaited_once_with("secret")
    submit_button.click.assert_awaited_once_with()
    assert len(tab.evaluate_calls) == 1


@pytest.mark.anyio
async def test_fill_login_form_retries_submit_after_data_request_failure_modal() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    email_input = _DummyElement()
    password_input = _DummyElement()
    submit_button = _DummyElement()
    tab.select_map = {
        'input[name="email"], input#login-email-input': email_input,
        'input[name="password"], input#login-password-input': password_input,
        'button[type="submit"], .login__button': submit_button,
    }
    tab.evaluate_result = True
    session = NodriverBrowserSession(
        browser=_DummyBrowser(tab),
        tab=tab,
    )

    result = await provider._fill_login_form(session, "user@example.com", "secret")

    assert result is True
    assert submit_button.click.await_count == 2
    assert len(tab.evaluate_calls) == 1


@pytest.mark.anyio
async def test_fill_login_form_skips_retry_when_data_request_failure_modal_missing() -> None:
    provider = _make_auth_provider()
    tab = _DummyTab()
    email_input = _DummyElement()
    password_input = _DummyElement()
    submit_button = _DummyElement()
    tab.select_map = {
        'input[name="email"], input#login-email-input': email_input,
        'input[name="password"], input#login-password-input': password_input,
        'button[type="submit"], .login__button': submit_button,
    }
    tab.evaluate_result = False
    session = NodriverBrowserSession(
        browser=_DummyBrowser(tab),
        tab=tab,
    )

    result = await provider._fill_login_form(session, "user@example.com", "secret")

    assert result is True
    submit_button.click.assert_awaited_once_with()
    assert len(tab.evaluate_calls) == 1


@pytest.mark.anyio
async def test_login_tab_prefers_web_page_over_chrome_ui_tab() -> None:
    provider = _make_auth_provider()
    coupang_tab = _DummyTab()
    coupang_tab.url = COUPANG_HOME_URL
    chrome_ui_tab = _DummyTab()
    chrome_ui_tab.url = "chrome://omnibox-popup.top-chrome/"
    runtime_browser = _DummyBrowser(coupang_tab)
    runtime_browser.tabs = [coupang_tab, chrome_ui_tab]
    session = NodriverBrowserSession(
        browser=runtime_browser,
        tab=coupang_tab,
    )

    assert provider._login_tab(session) is coupang_tab


def test_default_store_uses_provider_paths() -> None:
    provider = _make_auth_provider()

    assert isinstance(provider.store, ProviderStore)
    assert provider.store.credentials_path == provider.store.paths.credentials_path
    assert provider.store.paths.base_dir == Path.home() / ".k-commerce" / "coupang"
    assert provider.store.base_dir == Path.home() / ".k-commerce" / "coupang"


def test_store_can_be_replaced_with_overridden_root_dir(tmp_path: Path) -> None:
    provider = CoupangAuthService(
        provider_name="coupang",
        store=ProviderStore(ProviderPaths("coupang", root_dir=tmp_path)),
        browser=NodriverBrowser(),
    )

    assert isinstance(provider.store, ProviderStore)
    assert provider.store.paths.base_dir == tmp_path / "coupang"
    assert provider.store.credentials_path == tmp_path / "coupang" / "credentials.json"
    assert provider.store.base_dir == tmp_path / "coupang"


@pytest.mark.anyio
async def test_restore_session_uses_cookies_file_when_present() -> None:
    provider = _make_auth_provider()
    browser = _BrowserSpy()
    provider.browser = browser
    with tempfile.TemporaryDirectory() as temp_dir:
        provider.store = ProviderStore(ProviderPaths("coupang", root_dir=Path(temp_dir)))
        provider.store.base_dir.mkdir(parents=True)
        provider.store.cookies_file.write_text("cookies", encoding="utf-8")
        await provider._restore_session()

    browser.launch.assert_awaited_once_with(provider.store.paths)


@pytest.mark.anyio
async def test_restore_session_skips_launch_without_cookies_file() -> None:
    provider = _make_auth_provider()
    browser = _BrowserSpy()
    provider.browser = browser
    with tempfile.TemporaryDirectory() as temp_dir:
        provider.store = ProviderStore(ProviderPaths("coupang", root_dir=Path(temp_dir)))
        restored = await provider._restore_session()

    assert restored is None
    browser.launch.assert_not_awaited()


@pytest.mark.anyio
async def test_login_with_credentials_uses_browser_form_submission() -> None:
    provider = _make_auth_provider()
    browser = _BrowserSpy()
    session = types.SimpleNamespace(tab=_DummyTab())
    browser.launch = AsyncMock(return_value=session)
    provider.browser = browser
    provider._fill_login_form = AsyncMock(return_value=True)
    provider._wait_for_session_login = AsyncMock(return_value=True)

    result = await provider._login_with_credentials(type("Creds", (), {"email": "user@example.com", "password": "secret"})())

    assert result is True
    assert session.tab.get_calls == [COUPANG_LOGIN_URL]
    provider._fill_login_form.assert_awaited_once_with(session, "user@example.com", "secret")



@pytest.mark.anyio
async def test_persist_session_saves_cookies_and_metadata() -> None:
    provider = _make_auth_provider()
    browser = _BrowserSpy()
    session = object()
    provider.browser = browser
    provider._browser_session = session
    with tempfile.TemporaryDirectory() as temp_dir:
        provider.store = ProviderStore(ProviderPaths("coupang", root_dir=Path(temp_dir)))
        await provider._persist_session("automatic")
        metadata = provider.store.session_meta_path.read_text(encoding="utf-8")

    browser.save_session.assert_awaited_once_with(session, provider.store.cookies_file)
    assert '"login_method": "automatic"' in metadata


@pytest.mark.anyio
async def test_wait_for_manual_login_delegates_to_browser() -> None:
    provider = _make_auth_provider()
    browser = _BrowserSpy()
    session = types.SimpleNamespace(tab=object())
    provider.browser = browser
    provider._browser_session = session
    provider._is_logged_in = AsyncMock(return_value=True)

    assert await provider._wait_for_manual_login() is True
    provider._is_logged_in.assert_awaited_once_with(session.tab)


@pytest.mark.anyio
async def test_close_browser_session_handles_non_awaitable_stop() -> None:
    provider = _make_auth_provider()
    session = NodriverBrowserSession(
        browser=types.SimpleNamespace(stop=lambda: None),
        tab=_DummyTab(),
    )
    provider._browser_session = session

    await provider._close_browser_session()

    assert provider._browser_session is None


@pytest.mark.anyio
async def test_login_status_opens_home_checks_state_and_closes_browser_session(
    tmp_path: Path,
) -> None:
    provider = CoupangProvider(provider_name="coupang", root_dir=tmp_path)
    session = types.SimpleNamespace(tab=_DummyTab())
    provider._auth._is_logged_in = AsyncMock(return_value=True)
    cookies_file = tmp_path / "coupang" / "cookies.dat"
    cookies_file.parent.mkdir(parents=True)
    cookies_file.write_text("cookies", encoding="utf-8")

    with (
        patch.object(provider._browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider._browser, "close", new=AsyncMock()) as close,
    ):
        result = await provider.status()

    assert result == StatusResult(
        provider="coupang",
        logged_in=True,
        message="쿠팡 로그인 상태입니다",
    )
    launch.assert_awaited_once_with(provider.store.paths)
    assert session.tab.get_calls == [COUPANG_HOME_URL]
    provider._auth._is_logged_in.assert_awaited_once_with(session.tab)
    close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_login_status_closes_browser_session_when_home_check_fails(
    tmp_path: Path,
) -> None:
    provider = CoupangProvider(provider_name="coupang", root_dir=tmp_path)
    session = types.SimpleNamespace(tab=_DummyTab())
    session.tab.get = AsyncMock(side_effect=RuntimeError("boom"))
    cookies_file = tmp_path / "coupang" / "cookies.dat"
    cookies_file.parent.mkdir(parents=True)
    cookies_file.write_text("cookies", encoding="utf-8")

    with (
        patch.object(provider._browser, "launch", new=AsyncMock(return_value=session)),
        patch.object(provider._browser, "close", new=AsyncMock()) as close,
        pytest.raises(RuntimeError, match="boom"),
    ):
        await provider.status()

    close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_login_status_returns_logged_out_without_launch_on_clean_root(
    tmp_path: Path,
) -> None:
    provider = CoupangProvider(provider_name="coupang", root_dir=tmp_path)
    with (
        patch.object(provider._browser, "launch", new=AsyncMock()) as launch,
        patch.object(provider._browser, "close", new=AsyncMock()) as close,
    ):
        result = await provider.status()

    assert result == StatusResult(
        provider="coupang",
        logged_in=False,
        message="쿠팡 로그인 상태가 아닙니다",
    )
    launch.assert_not_awaited()
    close.assert_not_awaited()
    assert provider.store.base_dir == tmp_path / "coupang"
    assert not provider.store.base_dir.exists()
