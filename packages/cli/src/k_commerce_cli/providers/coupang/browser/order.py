from __future__ import annotations

import re

from k_commerce_cli.types import OrderListEntry

COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"


class CoupangOrderBrowser:
    async def open_order_list(self, session: object) -> None:
        await session.tab.get(COUPANG_ORDER_LIST_URL)

    async def read_order_page_state(self, tab: object) -> dict[str, object]:
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
        return {
            "url": page_url,
            "ready": (not has_loading_indicator) and (has_order_signals or has_empty_state),
            "has_login_prompt": has_login_prompt or "login.coupang.com" in page_url,
            "has_order_signals": has_order_signals,
            "has_empty_state": has_empty_state,
            "has_loading_indicator": has_loading_indicator,
        }

    async def read_visible_orders(self, tab: object) -> tuple[OrderListEntry, ...]:
        order_root = await self._safe_select(tab, '[class*="my-area-contents"] > div')
        if order_root is None:
            order_root = await self._safe_select(tab, '[class*="my-area-contents"]')
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
                        title=title,
                        quantity=quantity,
                        status=status,
                    )
                )

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

    async def _extract_title(self, item_node: object) -> str:
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

    def _children(self, node: object) -> list[object]:
        children = getattr(node, "children", [])
        return children if isinstance(children, list) else []

    def _looks_like_order_group(self, text: str) -> bool:
        return bool(re.match(r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\s*주문", text)) and "주문 상세보기" in text

    def _normalize_text(self, value: object) -> str:
        text = getattr(value, "text_all", value)
        return " ".join(str(text or "").split())

    async def _query_all(self, node: object, selector: str) -> list[object]:
        query = getattr(node, "query_selector_all", None)
        if not callable(query):
            return []
        try:
            results = await query(selector)
        except Exception:
            return []
        return results if isinstance(results, list) else []

    async def _safe_select(self, tab: object, selector: str) -> object | None:
        select = getattr(tab, "select", None)
        if not callable(select):
            return None
        try:
            return await select(selector, timeout=1)
        except Exception:
            return None

    async def _selector_exists(self, tab: object, selector: str) -> bool:
        return await self._safe_select(tab, selector) is not None


__all__ = ["COUPANG_ORDER_LIST_URL", "CoupangOrderBrowser"]
