from __future__ import annotations

import asyncio
from datetime import datetime
import inspect
from typing import Any

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, Store
from k_commerce_cli.services.providers.coupang.types import (
    CoupangDeliveryGroup,
    CoupangOrderList,
    CoupangOrderListResult,
    CoupangOrderMeta,
    CoupangOrderProduct,
    CoupangOrderResult,
    CoupangOrderSummary,
)

COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"


class CoupangOrderService:
    def __init__(
        self,
        provider_name: str,
        store: Store,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.store = store
        self.browser = browser
        self.terminal = terminal
        self._browser_session: BrowserSession | None = None

    async def list_orders(self, refresh: bool = False) -> CoupangOrderListResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 주문 수집을 시작합니다...")
        if not self.store.has_session():
            payload = self._empty_payload(refresh=refresh)
            return CoupangOrderListResult(
                message=format_coupang_order_list_message(payload),
                payload=payload,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_order_list(self._browser_session)
            years = await self._wait_for_visible_years()
            if not years:
                payload = self._empty_payload(refresh=refresh)
                return CoupangOrderListResult(
                    message=format_coupang_order_list_message(payload),
                    payload=payload,
                )

            if terminal is not None:
                terminal.info(f"수집 연도: {', '.join(years)}")
            orders, failed_pages = await self._collect_all_years(years, terminal)
            previous_orders = [] if refresh else self._load_previous_orders()
            summary = self._summarize_changes(previous_orders, orders)
            payload = self._build_payload(years, failed_pages, refresh, orders, summary)
            self.store.write_orders(payload.to_dict())
            return CoupangOrderListResult(
                message=format_coupang_order_list_message(payload),
                payload=payload,
            )
        finally:
            await self._close_browser_session()

    def _load_previous_orders(self) -> list[CoupangOrderResult]:
        previous = self.store.load_orders()
        if not previous:
            return []
        return CoupangOrderList.from_dict(previous).orders

    async def _read_visible_years(self) -> list[str]:
        years = await self._evaluate(
            """
            (() => Array.from(document.querySelectorAll('div, button, a, span'))
              .map((node) => (node.textContent || '').trim())
              .filter((text) => text === '최근 6개월' || /^20\\d{2}$/.test(text))
              .filter((text, index, items) => items.indexOf(text) === index))()
            """
        )
        return [year for year in years if year != "최근 6개월"]

    async def _open_order_list(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_ORDER_LIST_URL)

    async def _wait_for_visible_years(self, poll_count: int = 5) -> list[str]:
        for attempt in range(poll_count):
            years = await self._read_visible_years()
            if years:
                return years
            if attempt < poll_count - 1:
                await asyncio.sleep(1)
        return []

    async def _collect_all_years(
        self,
        years: list[str],
        terminal: Terminal | None,
    ) -> tuple[list[CoupangOrderResult], list[list[int | str]]]:
        collected: list[CoupangOrderResult] = []
        failed_pages: list[list[int | str]] = []
        for year in years:
            page_index = 0
            while True:
                if terminal is not None:
                    terminal.info(f"{year}년 {page_index + 1}페이지 수집 중...")
                try:
                    page = await self._fetch_page_with_retry(year, page_index)
                except Exception:
                    failed_pages.append([year, page_index + 1])
                    break
                collected.extend(self._build_order(order) for order in page["orderList"])
                pagination = page["orderPagination"]
                if not pagination["hasNext"]:
                    break
                page_index = pagination["nextPageIndex"]
        return collected, failed_pages

    async def _fetch_page_with_retry(self, year: str, page_index: int) -> dict[str, Any]:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                maybe_navigation = self._browser_session.tab.get(
                    f"{COUPANG_ORDER_LIST_URL}?requestYear={year}&pageIndex={page_index}"
                )
                if inspect.isawaitable(maybe_navigation):
                    await maybe_navigation
                return await self._wait_for_order_page_payload()
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(1)
        assert last_error is not None
        raise last_error

    async def _wait_for_order_page_payload(self, poll_count: int = 5) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(poll_count):
            try:
                return await self._evaluate(
                    """
                    (() => {
                      const script = document.querySelector('#__NEXT_DATA__');
                      if (!script?.textContent) {
                        throw new Error('missing __NEXT_DATA__');
                      }
                      const payload = JSON.parse(script.textContent);
                      return payload.props.pageProps.domains.desktopOrder;
                    })()
                    """
                )
            except Exception as exc:
                last_error = exc
                if attempt < poll_count - 1:
                    await asyncio.sleep(1)
        assert last_error is not None
        raise last_error

    async def _evaluate(self, expression: str) -> Any:
        if self._browser_session is None:
            raise RuntimeError("browser session is not available")
        result = await self._browser_session.tab.evaluate(expression)
        self._raise_if_exception_details(result)
        return self._unwrap_evaluated_value(result)

    def _raise_if_exception_details(self, value: Any) -> None:
        if value.__class__.__name__ != "ExceptionDetails":
            return

        remote_exception = getattr(value, "exception", None)
        description = getattr(remote_exception, "description", None)
        message = description or getattr(value, "text", None) or "browser evaluation failed"
        raise RuntimeError(str(message))

    def _unwrap_evaluated_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            if "type" in value:
                wrapped = value.get("value")
                if value["type"] == "null":
                    return None
                return self._unwrap_evaluated_value(wrapped)
            return {
                str(key): self._unwrap_evaluated_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            if all(
                isinstance(item, list) and len(item) == 2 and isinstance(item[0], str)
                for item in value
            ):
                return {
                    item[0]: self._unwrap_evaluated_value(item[1])
                    for item in value
                }
            return [self._unwrap_evaluated_value(item) for item in value]
        return value

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return
        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    def _build_order(self, data: dict[str, Any]) -> CoupangOrderResult:
        return CoupangOrderResult(
            provider=self.provider_name,
            orderId=int(data["orderId"]),
            title=str(data["title"]),
            orderedAt=int(data["orderedAt"]),
            totalProductPrice=int(data["totalProductPrice"]),
            deliveryGroupList=[
                CoupangDeliveryGroup(
                    shipmentBoxId=str(group["shipmentBoxId"]),
                    invoiceNumber=str(group["invoiceNumber"]),
                    invoiceStatus=str(group["invoiceStatus"]),
                    pddMessage={"message": self._read_message(group.get("pddMessage"))},
                    productList=[
                        CoupangOrderProduct(
                            vendorItemId=int(product["vendorItemId"]),
                            vendorItemName=str(product["vendorItemName"]),
                            productName=str(product["productName"]),
                            quantity=int(product["quantity"]),
                            unitPrice=int(product["unitPrice"]),
                            discountedUnitPrice=int(product["discountedUnitPrice"]),
                            combinedUnitPrice=int(product["combinedUnitPrice"]),
                            imagePath=str(product["imagePath"]),
                        )
                        for product in group.get("productList", [])
                    ],
                )
                for group in data.get("deliveryGroupList", [])
            ],
        )

    def _read_message(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        message = value.get("message")
        return str(message) if message is not None else None

    def _build_payload(
        self,
        years: list[str],
        failed_pages: list[list[int | str]],
        refresh: bool,
        orders: list[CoupangOrderResult],
        summary: CoupangOrderSummary,
    ) -> CoupangOrderList:
        return CoupangOrderList(
            meta=CoupangOrderMeta(
                provider=self.provider_name,
                collectedAt=datetime.now().astimezone().replace(microsecond=0).isoformat(),
                years=years,
                failedPages=failed_pages,
                refresh=refresh,
                summary=summary,
            ),
            orders=orders,
        )

    def _summarize_changes(
        self,
        previous_orders: list[CoupangOrderResult],
        current_orders: list[CoupangOrderResult],
    ) -> CoupangOrderSummary:
        previous_items = self._item_map(previous_orders)
        current_items = self._item_map(current_orders)

        added_orders = {
            key[0]
            for key in current_items.keys() - previous_items.keys()
        }
        deleted_orders = {
            key[0]
            for key in previous_items.keys() - current_items.keys()
        }
        updated_orders = {
            key[0]
            for key in current_items.keys() & previous_items.keys()
            if previous_items[key] != current_items[key]
        }
        return CoupangOrderSummary(
            totalOrders=len({order.orderId for order in current_orders}),
            addedOrders=len(added_orders),
            updatedOrders=len(updated_orders),
            deletedOrders=len(deleted_orders),
        )

    def _item_map(
        self,
        orders: list[CoupangOrderResult],
    ) -> dict[tuple[int, str, int], dict[str, Any]]:
        items: dict[tuple[int, str, int], dict[str, Any]] = {}
        for order in orders:
            for group in order.deliveryGroupList:
                for product in group.productList:
                    key = (
                        order.orderId,
                        group.shipmentBoxId,
                        product.vendorItemId,
                    )
                    items[key] = {
                        "provider": order.provider,
                        "orderId": order.orderId,
                        "title": order.title,
                        "orderedAt": order.orderedAt,
                        "totalProductPrice": order.totalProductPrice,
                        "shipmentBoxId": group.shipmentBoxId,
                        "invoiceNumber": group.invoiceNumber,
                        "invoiceStatus": group.invoiceStatus,
                        "pddMessage": group.pddMessage,
                        "product": product,
                    }
        return items

    def _empty_payload(self, *, refresh: bool) -> CoupangOrderList:
        return self._build_payload(
            years=[],
            failed_pages=[],
            refresh=refresh,
            orders=[],
            summary=CoupangOrderSummary(
                totalOrders=0,
                addedOrders=0,
                updatedOrders=0,
                deletedOrders=0,
            ),
        )


def format_coupang_order_list_message(payload: CoupangOrderList) -> str:
    meta = payload.meta
    summary = meta.summary
    failed_pages = meta.failedPages
    failed_suffix = ""
    if failed_pages:
        details = ", ".join(f"{year}년 {page}페이지" for year, page in failed_pages)
        failed_suffix = f", 실패 {len(failed_pages)}페이지({details})"

    if meta.refresh:
        return f"주문 새로 생성 완료: 총 {summary.totalOrders}건{failed_suffix}"

    return (
        f"주문 수집 완료: 총 {summary.totalOrders}건, "
        f"추가 {summary.addedOrders}건, 변경 {summary.updatedOrders}건, "
        f"삭제 {summary.deletedOrders}건{failed_suffix}"
    )
