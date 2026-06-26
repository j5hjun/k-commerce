from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import nodriver as uc

from k_commerce_cli.providers.paths import ProviderPaths

COUPANG_VIEWPORT = {"width": 1440, "height": 900}


class BrowserElement(Protocol):
    text_all: str
    children: list["BrowserElement"]

    async def query_selector_all(self, selector: str) -> list["BrowserElement"]: ...

    async def click(self) -> None: ...

    async def send_keys(self, text: str) -> None: ...


class BrowserTab(Protocol):
    url: str

    async def get(self, url: str) -> None: ...

    async def select(self, selector: str, timeout: int = 0) -> BrowserElement | None: ...


class BrowserCookies(Protocol):
    async def save(self, *, file: str) -> None: ...

    async def load(self, *, file: str) -> None: ...


class BrowserRuntime(Protocol):
    main_tab: BrowserTab | None
    tabs: list[BrowserTab]
    cookies: BrowserCookies

    async def get(self, url: str) -> BrowserTab: ...

    def stop(self) -> object: ...


@dataclass(frozen=True)
class CoupangBrowserSession:
    browser: BrowserRuntime
    tab: BrowserTab
    profile_dir: Path
    cookies_file: Path


class CoupangSessionBrowser:
    async def launch(self, paths: ProviderPaths) -> CoupangBrowserSession:
        profile_dir = paths.profile_dir
        cookies_file = paths.cookies_file
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
        await self._sleep_ms(1000)

    async def _sleep_ms(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)

    async def _ensure_tab(self, browser: BrowserRuntime) -> BrowserTab:
        main_tab = getattr(browser, "main_tab", None)
        if main_tab is not None:
            return main_tab
        return await browser.get("about:blank")

    async def _load_cookies(self, browser: BrowserRuntime, cookies_file: Path) -> None:
        if not cookies_file.is_file():
            return

        cookies_api = getattr(browser, "cookies", None)
        load = getattr(cookies_api, "load", None)
        if load is not None:
            await load(file=str(cookies_file))

    async def _safe_select(
        self, tab: BrowserTab, selector: str, timeout: int = 1
    ) -> BrowserElement | None:
        try:
            return await tab.select(selector, timeout=timeout)
        except Exception:
            await self._sleep_ms(250)
            try:
                return await tab.select(selector, timeout=timeout)
            except Exception:
                return None

    def _active_tab(self, session: CoupangBrowserSession) -> BrowserTab:
        tabs = getattr(session.browser, "tabs", None)
        candidates: list[BrowserTab] = []
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
