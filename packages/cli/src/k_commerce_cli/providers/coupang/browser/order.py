from __future__ import annotations

import asyncio
from datetime import date
import re
from typing import cast

from k_commerce_cli.types import OrderListEntry, OrderPageState, OrderStatus

from .session import BrowserElement, BrowserTab, CoupangBrowserSession

COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"
ORDER_PAGE_TURN_ATTEMPTS = 10
ORDER_PAGE_TURN_POLL_SECONDS = 0.2
ORDER_PAGE_MAX_PAGES = 32
ORDER_SCOPE_PATTERN = re.compile(r"^(최근\s*\d+개월|20\d{2})$")


class CoupangOrderBrowser:
    async def open_order_list(self, session: CoupangBrowserSession) -> None:
        await session.tab.get(COUPANG_ORDER_LIST_URL)

    async def read_order_page_state(self, tab: BrowserTab) -> OrderPageState:
        page_url = str(getattr(tab, "url", ""))
        has_login_prompt = await self._selector_exists(
            tab, 'input[type="password"], input[name="password"], form[action*="login"]'
        )
        has_order_signals = await self._selector_exists(
            tab,
            '[data-testid*="order"], [class*="my-area-contents"], [class*="my-area-body"], [class*="order"], [id*="order"]',
        )
        has_empty_state = await self._selector_exists(
            tab,
            '[class*="empty"], [class*="no-order"], [data-testid*="empty"]',
        )
        has_loading_indicator = await self._selector_exists(
            tab,
            '[aria-busy="true"], [class*="loading"], [class*="skeleton"], [class*="spinner"]',
        )
        return OrderPageState(
            url=page_url,
            ready=(not has_loading_indicator) and (has_order_signals or has_empty_state),
            has_login_prompt=has_login_prompt or "login.coupang.com" in page_url,
            has_order_signals=has_order_signals,
            has_empty_state=has_empty_state,
            has_loading_indicator=has_loading_indicator,
        )

    async def read_visible_orders(self, tab: BrowserTab) -> tuple[OrderListEntry, ...]:
        order_root = await self._order_root(tab)
        if order_root is None:
            return ()

        orders: list[OrderListEntry] = []
        seen_rows: set[str] = set()
        for group in self._children(order_root):
            group_text = self._normalize_text(group)
            if not self._looks_like_order_group(group_text):
                continue

            group_header_match = re.match(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\s*주문", group_text)
            group_header = group_header_match.group(0) if group_header_match else ""
            order_date = group_header.removesuffix(" 주문").strip()
            item_nodes = await self._query_all(group, 'tr, [class*="sc-5a139ee-0"], td')
            seen_item_texts: set[str] = set()
            for item_node in item_nodes:
                text = self._normalize_text(item_node)
                if not text or "장바구니 담기" not in text or text in seen_item_texts:
                    continue
                seen_item_texts.add(text)

                title = await self._extract_title(item_node)
                if not title:
                    continue

                status_match = re.search(
                    r"(결제완료|상품준비중|배송중|배송완료|취소|반품|교환|배송시작)",
                    text,
                )
                quantity_match = re.search(r"(?:\s|^)(\d+)개(?:\s|$)", text)
                status = status_match.group(1).strip() if status_match else ""
                raw_text = self._normalize_text(f"{group_header} {text}")
                if not self._looks_like_order_row(
                    title=title,
                    status=status,
                    has_detail_link="주문 상세보기" in group_text,
                    raw_text=raw_text,
                ):
                    continue

                quantity = 1
                if quantity_match:
                    try:
                        quantity = int(quantity_match.group(1))
                    except ValueError:
                        quantity = 1

                row_key = "|".join((title, str(quantity), status))
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)

                orders.append(
                    OrderListEntry(
                        order_date=order_date,
                        title=title,
                        quantity=quantity,
                        status=cast(OrderStatus, status),
                    )
                )

        return tuple(orders)

    async def read_all_orders(self, tab: BrowserTab) -> tuple[OrderListEntry, ...]:
        orders: list[OrderListEntry] = []
        seen_rows: set[str] = set()
        scope_labels = await self._scope_labels(tab)
        if not scope_labels:
            await self._collect_current_scope_orders(tab, orders, seen_rows)
            return tuple(orders)
        for scope_label in scope_labels:
            await self._activate_scope(tab, scope_label)
            await self._collect_current_scope_orders(tab, orders, seen_rows)

        return tuple(orders)

    async def read_orders_through_date(
        self,
        tab: BrowserTab,
        cutoff_order_date: str | None,
    ) -> tuple[OrderListEntry, ...]:
        orders: list[OrderListEntry] = []
        seen_rows: set[str] = set()
        cutoff_date = self._parse_order_date(cutoff_order_date)

        if await self._collect_scope_orders_through_date(tab, orders, seen_rows, cutoff_date):
            return tuple(orders)

        for scope_label in await self._scope_labels(tab):
            await self._activate_scope(tab, scope_label)
            if await self._collect_scope_orders_through_date(tab, orders, seen_rows, cutoff_date):
                break

        return tuple(orders)

    def _looks_like_order_row(
        self,
        *,
        title: str,
        status: str,
        has_detail_link: bool,
        raw_text: str,
    ) -> bool:
        if not title:
            return False

        has_known_status = status in {
            "결제완료",
            "상품준비중",
            "배송중",
            "배송완료",
            "취소",
            "반품",
            "교환",
        }
        normalized = " ".join(raw_text.split())
        has_order_date = "주문" in normalized and any(character.isdigit() for character in normalized)
        starts_with_order_date = normalized[:32].count("주문") > 0 and normalized[:16].count(".") >= 2
        return starts_with_order_date and has_order_date and has_detail_link and has_known_status

    async def _extract_title(self, item_node: BrowserElement) -> str:
        action_pattern = re.compile(r"주문 상세보기|배송 조회|교환, 반품 신청|리뷰 작성하기|판매자 문의|장바구니 담기|이전|다음")
        order_date_pattern = re.compile(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\s*주문")
        price_pattern = re.compile(r"\d{1,3}(,\d{3})*\s*원")
        for link in await self._query_all(item_node, "a"):
            link_text = self._normalize_text(link)
            if not link_text:
                continue
            if action_pattern.search(link_text) or order_date_pattern.search(link_text) or price_pattern.search(link_text):
                continue
            if len(link_text) >= 2:
                return link_text
        return ""

    def _children(self, node: BrowserElement) -> list[BrowserElement]:
        children = getattr(node, "children", [])
        return children if isinstance(children, list) else []

    def _looks_like_order_group(self, text: str) -> bool:
        return bool(re.match(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\s*주문", text)) and "주문 상세보기" in text

    def _normalize_text(self, value: BrowserElement | str) -> str:
        text = getattr(value, "text_all", value)
        return " ".join(str(text or "").split())

    async def _query_all(self, node: BrowserElement, selector: str) -> list[BrowserElement]:
        query = getattr(node, "query_selector_all", None)
        if not callable(query):
            return []
        try:
            results = await query(selector)
        except Exception:
            return []
        return results if isinstance(results, list) else []

    async def _safe_select(self, tab: BrowserTab, selector: str) -> BrowserElement | None:
        select = getattr(tab, "select", None)
        if not callable(select):
            return None
        try:
            return await select(selector, timeout=1)
        except Exception:
            return None

    async def _selector_exists(self, tab: BrowserTab, selector: str) -> bool:
        return await self._safe_select(tab, selector) is not None

    async def _order_root(self, tab: BrowserTab) -> BrowserElement | None:
        order_root = await self._safe_select(tab, '[class*="my-area-contents"] > div')
        if order_root is not None:
            return order_root
        return await self._safe_select(tab, '[class*="my-area-contents"]')

    async def _find_next_page_control(self, tab: BrowserTab) -> BrowserElement | None:
        order_root = await self._order_root(tab)
        if order_root is None:
            return None

        for control in await self._query_all(order_root, "button, a"):
            if self._normalize_text(control) == "다음":
                return control
        return None

    async def _page_snapshot(self, tab: BrowserTab) -> str:
        order_root = await self._order_root(tab)
        if order_root is None:
            return str(getattr(tab, "url", ""))
        return self._snapshot_text(order_root)

    async def _go_to_next_page(
        self,
        tab: BrowserTab,
        control: BrowserElement,
        current_snapshot: str,
    ) -> bool:
        return await self._click_and_settle(tab, control, current_snapshot)

    async def _collect_current_scope_orders(
        self,
        tab: BrowserTab,
        orders: list[OrderListEntry],
        seen_rows: set[str],
    ) -> None:
        for _ in range(ORDER_PAGE_MAX_PAGES):
            visible_orders = await self.read_visible_orders(tab)
            for order in visible_orders:
                row_key = "|".join((order.title, str(order.quantity), order.status))
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                orders.append(order)

            next_control = await self._find_next_page_control(tab)
            if next_control is None:
                break

            current_snapshot = await self._page_snapshot(tab)
            if not await self._go_to_next_page(tab, next_control, current_snapshot):
                break

    async def _collect_scope_orders_through_date(
        self,
        tab: BrowserTab,
        orders: list[OrderListEntry],
        seen_rows: set[str],
        cutoff_date: date | None,
    ) -> bool:
        for _ in range(ORDER_PAGE_MAX_PAGES):
            visible_orders = await self.read_visible_orders(tab)
            for order in visible_orders:
                row_key = "|".join((order.title, str(order.quantity), order.status))
                if row_key in seen_rows:
                    continue
                seen_rows.add(row_key)
                orders.append(order)

            if self._should_stop_after_orders(visible_orders, cutoff_date):
                return True

            next_control = await self._find_next_page_control(tab)
            if next_control is None:
                return False

            current_snapshot = await self._page_snapshot(tab)
            if not await self._go_to_next_page(tab, next_control, current_snapshot):
                return False

        return False

    async def _scope_labels(self, tab: BrowserTab) -> list[str]:
        scope_root = await self._scope_root(tab)
        if scope_root is None:
            return []

        labels: list[str] = []
        for control in self._scope_controls(scope_root):
            label = self._normalize_text(control)
            if not ORDER_SCOPE_PATTERN.match(label):
                continue
            if label == "최근 6개월":
                continue
            if label in labels:
                continue
            labels.append(label)
        return labels

    async def _activate_scope(self, tab: BrowserTab, scope_label: str) -> None:
        scope_root = await self._scope_root(tab)
        if scope_root is None:
            return

        for control in self._scope_controls(scope_root):
            if self._normalize_text(control) != scope_label:
                continue
            current_snapshot = await self._page_snapshot(tab)
            await self._click_and_settle(tab, control, current_snapshot)
            return

    async def _scope_root(self, tab: BrowserTab) -> BrowserElement | None:
        scope_root = await self._safe_select(tab, '[class*="my-area-body"]')
        if scope_root is not None:
            return scope_root
        return await self._order_root(tab)

    def _scope_controls(self, node: BrowserElement) -> list[BrowserElement]:
        controls: list[BrowserElement] = []
        self._collect_scope_controls(node, controls)
        return controls

    def _collect_scope_controls(
        self,
        node: BrowserElement,
        controls: list[BrowserElement],
    ) -> None:
        text = self._normalize_text(node)
        if ORDER_SCOPE_PATTERN.match(text) and self._is_clickable_scope_node(node):
            controls.append(node)
            return

        for child in self._children(node):
            self._collect_scope_controls(child, controls)

    def _is_clickable_scope_node(self, node: BrowserElement) -> bool:
        if callable(getattr(node, "click", None)):
            return True
        for attribute in ("role", "tabindex", "href", "onclick"):
            value = self._get_attribute(node, attribute)
            if value:
                return True
        return str(getattr(node, "cursor", "")).strip().lower() == "pointer"

    def _get_attribute(self, node: BrowserElement, name: str) -> str:
        getter = getattr(node, "get_attribute", None)
        if callable(getter):
            try:
                value = getter(name)
            except Exception:
                return ""
            return "" if value is None else str(value)
        return ""

    async def _click_and_settle(
        self,
        tab: BrowserTab,
        control: BrowserElement,
        current_snapshot: str,
    ) -> bool:
        click = getattr(control, "click", None)
        if not callable(click):
            return False

        try:
            await click()
        except Exception:
            return False

        for _ in range(ORDER_PAGE_TURN_ATTEMPTS):
            await asyncio.sleep(ORDER_PAGE_TURN_POLL_SECONDS)
            if await self._page_snapshot(tab) != current_snapshot:
                return True
        return False

    def _snapshot_text(self, node: BrowserElement) -> str:
        parts = [self._normalize_text(node)]
        for child in self._children(node):
            parts.append(self._snapshot_text(child))
        return " ".join(part for part in parts if part).strip()

    def _should_stop_after_orders(
        self,
        orders: tuple[OrderListEntry, ...],
        cutoff_date: date | None,
    ) -> bool:
        if cutoff_date is None or not orders:
            return False

        oldest_visible = min(
            (
                parsed
                for parsed in (self._parse_order_date(order.order_date) for order in orders)
                if parsed is not None
            ),
            default=None,
        )
        return oldest_visible is not None and oldest_visible < cutoff_date

    def _parse_order_date(self, raw: str | None) -> date | None:
        if not raw:
            return None
        match = re.match(r"^\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\s*$", raw)
        if match is None:
            return None
        year, month, day = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None


__all__ = ["COUPANG_ORDER_LIST_URL", "CoupangOrderBrowser"]
