from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Protocol

from k_commerce_cli.providers.base import OrderProvider
from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.store import ProviderStore
from k_commerce_cli.types import OrderListEntry, OrderListResult, OrderPageState
from .browser.session import BrowserTab
from .browser import CoupangBrowserSession
from .browser.order import CoupangOrderBrowser

ORDER_PAGE_STATE_ATTEMPTS = 3
ORDER_PAGE_STATE_POLL_SECONDS = 0.2
TERMINAL_ORDER_STATUSES = {"배송완료", "취소", "반품", "교환"}


class OrderSessionProvider(Protocol):
    name: ProviderName

    async def restore_valid_session(
        self, root_dir: Path | None = None
    ) -> CoupangBrowserSession | None: ...

    async def close_session(self) -> None: ...


class CoupangOrderProvider(OrderProvider):
    def __init__(self, auth_provider: OrderSessionProvider) -> None:
        self.auth_provider = auth_provider
        self.order_browser = CoupangOrderBrowser()

    async def list(
        self,
        root_dir: Path | None = None,
        refresh: bool = False,
    ) -> OrderListResult:
        store = ProviderStore(
            ProviderPaths(self.auth_provider.name, root_dir or Path.home() / ".k-commerce")
        )
        cached_orders = () if refresh else store.load_order_cache()

        restored_session = await self.auth_provider.restore_valid_session(root_dir)
        if restored_session is None:
            if cached_orders:
                return OrderListResult(
                    provider=self.auth_provider.name,
                    success=True,
                    message=f"주문 {len(cached_orders)}건을 찾았습니다.",
                    orders=cached_orders,
                )
            return OrderListResult(
                provider=self.auth_provider.name,
                success=False,
                message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                orders=(),
            )

        try:
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

            cutoff_order_date = self._refresh_cutoff_order_date(cached_orders)
            if refresh or (cutoff_order_date is None and not cached_orders):
                orders = await self.order_browser.read_all_orders(restored_session.tab)
            else:
                orders = await self.order_browser.read_orders_through_date(
                    restored_session.tab,
                    cutoff_order_date,
                )
            if refresh:
                store.write_order_cache(orders)
            else:
                orders = store.merge_order_cache(orders)
            return OrderListResult(
                provider=self.auth_provider.name,
                success=True,
                message=f"주문 {len(orders)}건을 찾았습니다.",
                orders=orders,
            )
        finally:
            await self.auth_provider.close_session()

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

    def _refresh_cutoff_order_date(self, cached_orders: tuple[OrderListEntry, ...]) -> str | None:
        active_dates = [
            parsed
            for parsed in (
                self._parse_order_date(order.order_date)
                for order in cached_orders
                if getattr(order, "status", None) not in TERMINAL_ORDER_STATUSES
            )
            if parsed is not None
        ]
        if active_dates:
            return self._format_order_date(min(active_dates))

        cached_dates = [
            parsed
            for parsed in (self._parse_order_date(order.order_date) for order in cached_orders)
            if parsed is not None
        ]
        if not cached_dates:
            return None
        return self._format_order_date(max(cached_dates))

    def _parse_order_date(self, raw: str) -> date | None:
        try:
            year_str, month_str, day_str = (part.strip() for part in raw.split("."))
            return date(int(year_str), int(month_str), int(day_str))
        except (TypeError, ValueError):
            return None

    def _format_order_date(self, value: date) -> str:
        return f"{value.year}. {value.month}. {value.day}"
