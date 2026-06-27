from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import nodriver as uc

from k_commerce_cli.services.base import BrowserElement, BrowserTab
from k_commerce_cli.services.paths import ProviderPaths

DEFAULT_VIEWPORT = {"width": 1440, "height": 900}


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
class NodriverBrowserSession:
    browser: BrowserRuntime
    tab: BrowserTab


class NodriverBrowser:
    async def launch(self, paths: ProviderPaths) -> NodriverBrowserSession:
        profile_dir = paths.profile_dir
        cookies_file = paths.cookies_file
        profile_dir.mkdir(parents=True, exist_ok=True)

        browser = await uc.start(
            headless=False,
            user_data_dir=str(profile_dir),
            browser_args=[
                f"--window-size={DEFAULT_VIEWPORT['width']},{DEFAULT_VIEWPORT['height']}",
                "--lang=ko-KR",
            ],
            lang="ko-KR",
        )
        tab = await self._ensure_tab(browser)
        await self._load_cookies(browser, cookies_file)
        return NodriverBrowserSession(browser=browser, tab=tab)

    async def save_session(self, session: NodriverBrowserSession, cookies_file: Path) -> None:
        cookies_api = getattr(session.browser, "cookies", None)
        save = getattr(cookies_api, "save", None)
        if save is not None:
            await save(file=str(cookies_file))

    async def close(self, session: NodriverBrowserSession) -> None:
        stop = getattr(session.browser, "stop", None)
        if stop is not None:
            result = stop()
            if inspect.isawaitable(result):
                await result
        await asyncio.sleep(1)

    async def select(
        self,
        tab: BrowserTab,
        selector: str,
        timeout: int = 1,
    ) -> BrowserElement | None:
        try:
            return await tab.select(selector, timeout=timeout)
        except Exception:
            await asyncio.sleep(0.25)
            try:
                return await tab.select(selector, timeout=timeout)
            except Exception:
                return None

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
