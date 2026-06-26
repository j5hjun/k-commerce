from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from k_commerce_cli.providers.base import OrderProvider
from k_commerce_cli.types import OrderListResult, OrderPageState
from .browser.session import BrowserTab
from .browser.order import CoupangOrderBrowser

ORDER_PAGE_STATE_ATTEMPTS = 3
ORDER_PAGE_STATE_POLL_SECONDS = 0.2

if TYPE_CHECKING:
    from .auth import CoupangAuthProvider


class CoupangOrderProvider(OrderProvider):
    def __init__(self, auth_provider: "CoupangAuthProvider") -> None:
        self.auth_provider = auth_provider
        self.order_browser = CoupangOrderBrowser()

    async def list_orders(self, root_dir: Path | None = None) -> OrderListResult:
        self.auth_provider._configure_paths(root_dir)
        restored_session = await self.auth_provider._restore_session()
        if restored_session is None:
            return OrderListResult(
                provider=self.auth_provider.name,
                success=False,
                message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                orders=(),
            )

        try:
            if not await self.auth_provider._verify_session(restored_session):
                return OrderListResult(
                    provider=self.auth_provider.name,
                    success=False,
                    message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                    orders=(),
                )

            await self.order_browser.open_order_list(restored_session)
            page_state = await self._wait_for_order_page(restored_session.tab)
            if page_state.has_login_prompt:
                return OrderListResult(
                    provider=self.auth_provider.name,
                    success=False,
                    message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                    orders=(),
                )
            if not page_state.ready:
                return OrderListResult(
                    provider=self.auth_provider.name,
                    success=False,
                    message="쿠팡 주문 페이지를 불러오지 못했습니다.",
                    orders=(),
                )

            orders = await self.order_browser.read_visible_orders(restored_session.tab)
            return OrderListResult(
                provider=self.auth_provider.name,
                success=True,
                message=f"주문 {len(orders)}건을 찾았습니다.",
                orders=orders,
            )
        finally:
            await self.auth_provider._close_browser_session()

    async def _wait_for_order_page(self, tab: BrowserTab) -> OrderPageState:
        page_state = OrderPageState(
            url=str(getattr(tab, "url", "")),
            ready=False,
            has_login_prompt=False,
            has_order_signals=False,
            has_empty_state=False,
            has_loading_indicator=False,
        )

        for attempt in range(ORDER_PAGE_STATE_ATTEMPTS):
            page_state = await self.order_browser.read_order_page_state(tab)
            if page_state.has_login_prompt or page_state.ready:
                return page_state
            if attempt + 1 < ORDER_PAGE_STATE_ATTEMPTS:
                await asyncio.sleep(ORDER_PAGE_STATE_POLL_SECONDS)

        return page_state
