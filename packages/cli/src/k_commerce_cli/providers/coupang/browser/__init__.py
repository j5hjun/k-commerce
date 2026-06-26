from __future__ import annotations

from .auth import (
    COUPANG_HOME_URL,
    COUPANG_LOGIN_LINK_SELECTOR,
    COUPANG_LOGIN_URL,
    COUPANG_MYCOUPANG_SELECTOR,
    CoupangAuthBrowser,
)
from .session import BrowserTab, COUPANG_VIEWPORT, CoupangBrowserSession, CoupangSessionBrowser


class CoupangBrowser:
    """Compatibility wrapper over the split browser helpers."""

    def __init__(self) -> None:
        self.session = CoupangSessionBrowser()
        self.auth = CoupangAuthBrowser(self.session)

    async def launch(self, paths) -> CoupangBrowserSession:
        return await self.session.launch(paths)

    async def open_home(self, session: CoupangBrowserSession) -> None:
        await self.auth.open_home(session)

    async def open_login(self, session: CoupangBrowserSession) -> None:
        await self.auth.open_login(session)

    async def open_login_entry(self, session: CoupangBrowserSession) -> None:
        await self.auth.open_login_entry(session)

    async def is_logged_in(self, tab: BrowserTab) -> bool:
        return await self.auth.is_logged_in(tab)

    async def wait_for_manual_login(
        self,
        session: CoupangBrowserSession,
        poll_count: int = 300,
    ) -> bool:
        return await self.auth.wait_for_manual_login(session, poll_count=poll_count)

    async def save_session(self, session: CoupangBrowserSession) -> None:
        await self.session.save_session(session)

    async def close(self, session: CoupangBrowserSession) -> None:
        await self.session.close(session)

    async def fill_login_form(
        self,
        session: CoupangBrowserSession,
        email: str,
        password: str,
    ) -> bool:
        return await self.auth.fill_login_form(session, email, password)

    def _active_tab(self, session: CoupangBrowserSession) -> BrowserTab:
        return self.session._active_tab(session)


__all__ = [
    "COUPANG_HOME_URL",
    "COUPANG_LOGIN_LINK_SELECTOR",
    "COUPANG_LOGIN_URL",
    "COUPANG_MYCOUPANG_SELECTOR",
    "COUPANG_VIEWPORT",
    "CoupangAuthBrowser",
    "CoupangBrowser",
    "CoupangBrowserSession",
    "CoupangSessionBrowser",
]
