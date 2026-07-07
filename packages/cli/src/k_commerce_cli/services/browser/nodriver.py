from __future__ import annotations

import asyncio
import contextlib
import inspect
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import nodriver as uc

from k_commerce_cli.services.base import Browser, BrowserElement, BrowserSession, BrowserTab
from k_commerce_cli.services.paths import ProviderPaths


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
class NodriverBrowserSession(BrowserSession):
    browser: BrowserRuntime
    tab: BrowserTab


_BROWSER_LAUNCH_ATTEMPTS = 2
_BROWSER_LAUNCH_RETRY_DELAY_SECONDS = 1.0


def _is_transient_browser_launch_error(exc: BaseException) -> bool:
    if isinstance(exc, (ConnectionError, OSError)):
        return True
    message = str(exc).lower()
    return "connect to browser" in message or "failed to connect" in message


class NodriverBrowser(Browser):
    async def launch(self, paths: ProviderPaths) -> NodriverBrowserSession:
        profile_dir = paths.profile_dir
        cookies_file = paths.cookies_file
        profile_dir.mkdir(parents=True, exist_ok=True)

        browser = await self._start_browser(profile_dir)
        tab = await self._ensure_tab(browser)
        await self._load_cookies(browser, cookies_file)
        return NodriverBrowserSession(browser=browser, tab=tab)

    async def _start_browser(self, profile_dir: Path) -> BrowserRuntime:
        last_error: BaseException | None = None
        for attempt in range(_BROWSER_LAUNCH_ATTEMPTS):
            try:
                return await uc.start(
                    headless=False,
                    user_data_dir=str(profile_dir),
                    browser_args=[
                        "--window-size=1440,900",
                        "--lang=ko-KR",
                    ],
                    lang="ko-KR",
                    sandbox=_browser_sandbox_enabled(),
                )
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= _BROWSER_LAUNCH_ATTEMPTS or not _is_transient_browser_launch_error(exc):
                    raise
                await asyncio.sleep(_BROWSER_LAUNCH_RETRY_DELAY_SECONDS)
        assert last_error is not None
        raise last_error

    async def save_session(self, session: NodriverBrowserSession, cookies_file: Path) -> None:
        cookies_api = getattr(session.browser, "cookies", None)
        save = getattr(cookies_api, "save", None)
        if save is not None:
            await save(file=str(cookies_file))

    async def close(self, session: NodriverBrowserSession) -> None:
        browser = session.browser

        aclose = getattr(browser, "aclose", None)
        if callable(aclose):
            with contextlib.suppress(Exception):
                await aclose()

        process = getattr(browser, "_process", None)
        if process is not None:
            with contextlib.suppress(Exception):
                transport = getattr(process, "_transport", None)
                if transport is not None:
                    transport.close()
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except TimeoutError:
                        process.kill()
                        await process.wait()
                for pipe_name in ("stdin", "stdout", "stderr"):
                    pipe = getattr(process, pipe_name, None)
                    if pipe is not None:
                        close = getattr(pipe, "close", None)
                        if callable(close):
                            close()
            browser._process = None
            if hasattr(browser, "_process_pid"):
                browser._process_pid = None
            return

        stop = getattr(browser, "stop", None)
        if stop is not None:
            result = stop()
            if inspect.isawaitable(result):
                with contextlib.suppress(Exception):
                    await result

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
        main_tab = None
        try:
            main_tab = browser.main_tab
        except (StopIteration, RuntimeError):
            main_tab = None
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


def _browser_sandbox_enabled() -> bool:
    value = os.environ.get("K_COMMERCE_BROWSER_SANDBOX")
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}
