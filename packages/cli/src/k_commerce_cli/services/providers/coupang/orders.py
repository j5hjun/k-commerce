from __future__ import annotations

from datetime import date, datetime
import inspect
from typing import Any
from urllib.parse import urlencode

import anyio

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, Store
from k_commerce_cli.services.providers.coupang.types import (
    CoupangDeliveryGroup,
    CoupangOrderList,
    CoupangOrderMeta,
    CoupangOrderProduct,
    CoupangOrderResult,
    CoupangOrderSummary,
)
from k_commerce_cli.services.providers.coupang.result_metadata import (
    BROWSER_CLOSED_METADATA,
    EMPTY_METADATA,
    LOGIN_REQUIRED_METADATA,
    ResultMetadata,
    is_browser_closed_error,
)
from k_commerce_cli.services.types import (
    OrderDetailItem,
    OrderDetailRequest,
    OrderDetailResult,
    OrderFailureItem,
    OrderFailuresRequest,
    OrderFailuresResult,
    OrderListItem,
    OrderListRequest,
    OrderListResult,
    OrderSyncRequest,
    OrderSyncResult,
    ProviderName,
)

COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"


class CoupangOrderService:
    def __init__(
        self,
        provider: ProviderName,
        store: Store,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider = provider
        self.store = store
        self.browser = browser
        self.terminal = terminal
        self._browser_session: BrowserSession | None = None

    async def sync_orders(self, request: OrderSyncRequest) -> OrderSyncResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 주문 수집을 시작합니다...")
        if not self.store.has_session():
            payload = self._empty_payload(refresh=request.refresh)
            return self._not_logged_in_order_result(payload)

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_order_list(self._browser_session)
            if await self._is_order_login_page():
                payload = self._empty_payload(refresh=request.refresh)
                return self._not_logged_in_order_result(payload)
            if request.failed_only:
                payload = await self._retry_failed_pages(terminal)
                self.store.write_orders(payload.to_dict())
                self._emit_order_result(terminal, payload)
                return self._order_sync_result(payload, request)

            years = await self._wait_for_visible_years()
            if not years:
                payload = self._empty_payload(refresh=request.refresh)
                self._emit_order_result(terminal, payload)
                return self._order_sync_result(payload, request, ResultMetadata(error_code="order_page_unavailable", retryable=True))

            previous = None if request.refresh else self._load_previous_order_list()
            if terminal is not None:
                terminal.info(f"수집 연도: {', '.join(years)}")
            orders, failed_pages = await self._collect_all_years(
                years,
                terminal,
                cache=previous,
            )
            previous_orders = [] if previous is None else previous.orders
            summary = self._summarize_changes(previous_orders, orders)
            payload = self._build_payload(years, failed_pages, request.refresh, orders, summary)
            self.store.write_orders(payload.to_dict())
            self._emit_order_result(terminal, payload)
            return self._order_sync_result(payload, request)
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            payload = self._empty_payload(refresh=request.refresh)
            if terminal is not None:
                terminal.warn("브라우저가 닫혀 주문 수집을 완료하지 못했습니다.")
            return self._browser_closed_order_result(payload, request)
        finally:
            await self._close_browser_session()

    async def list_orders(self, request: OrderListRequest) -> OrderListResult:
        payload = self._load_previous_order_list()
        if payload is None:
            return self._sync_required_order_list_result(request)

        matching_orders = self._filter_orders(payload.orders, request.start_date, request.end_date, request.status)
        offset = 0 if request.cursor is None else int(request.cursor)
        page = matching_orders[offset : offset + request.limit]
        next_offset = offset + request.limit
        has_more = next_offset < len(matching_orders)
        return OrderListResult(
            success=True,
            provider=self.provider.value,
            message=f"저장된 주문 조회 완료: {len(page)}건(전체 {len(matching_orders)}건)",
            start_date=request.start_date,
            end_date=request.end_date,
            count=len(page),
            total_count=len(matching_orders),
            has_more=has_more,
            next_cursor=str(next_offset) if has_more else None,
            orders=tuple(self._order_list_item(order) for order in page),
        )

    async def get_order_detail(self, request: OrderDetailRequest) -> OrderDetailResult:
        payload = self._load_previous_order_list()
        if payload is None:
            return OrderDetailResult(
                success=False,
                provider=self.provider.value,
                message="저장된 주문 데이터가 없습니다. 먼저 주문 수집이 필요합니다.",
                order_id=request.order_id,
                error_code="sync_required",
                next_tools=("order_sync",),
            )

        for order in payload.orders:
            if str(order.orderId) == request.order_id:
                return OrderDetailResult(
                    success=True,
                    provider=self.provider.value,
                    message="저장된 주문 상세 조회 완료",
                    order_id=str(order.orderId),
                    ordered_at=self._ordered_at_date_text(order),
                    status=self._order_status(order),
                    title=order.title,
                    amount=order.totalProductPrice,
                    items=tuple(self._order_detail_items(order)),
                )
        return OrderDetailResult(
            success=False,
            provider=self.provider.value,
            message="저장된 주문에서 해당 주문을 찾지 못했습니다.",
            order_id=request.order_id,
            error_code="order_not_found",
            next_tools=("order_list",),
        )

    async def list_order_failures(self, request: OrderFailuresRequest) -> OrderFailuresResult:
        payload = self._load_previous_order_list()
        if payload is None:
            return OrderFailuresResult(
                success=False,
                provider=self.provider.value,
                message="저장된 주문 데이터가 없습니다. 먼저 주문 수집이 필요합니다.",
                start_date=request.start_date,
                end_date=request.end_date,
                count=0,
                orders=(),
                error_code="sync_required",
                next_tools=("order_sync",),
            )

        matching_orders = [
            order for order in self._filter_orders(payload.orders, request.start_date, request.end_date, "all") if self._is_failure_order(order)
        ][: request.limit]
        return OrderFailuresResult(
            success=True,
            provider=self.provider.value,
            message=f"저장된 주문 처리 필요 항목 조회 완료: {len(matching_orders)}건",
            start_date=request.start_date,
            end_date=request.end_date,
            count=len(matching_orders),
            orders=tuple(self._order_failure_item(order) for order in matching_orders),
        )

    def _load_previous_orders(self) -> list[CoupangOrderResult]:
        previous = self._load_previous_order_list()
        if previous is None:
            return []
        return previous.orders

    def _load_previous_order_list(self) -> CoupangOrderList | None:
        previous = self.store.load_orders()
        if not previous:
            return None
        return CoupangOrderList.from_dict(previous)

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

    async def _is_order_login_page(self) -> bool:
        try:
            state = await self._evaluate(
                """
                (() => ({
                  url: window.location.href,
                  body_text: document.body?.innerText || '',
                  has_password_input:
                    document.querySelector('input[type="password"], input[name="password"], #login-password-input') !== null
                }))()
                """
            )
        except RuntimeError as exc:
            if is_browser_closed_error(exc):
                raise
            return False
        if not isinstance(state, dict):
            return False

        page_url = str(state.get("url", ""))
        body_text = str(state.get("body_text", ""))
        has_password_input = bool(state.get("has_password_input"))
        return (
            "login.coupang.com" in page_url
            or "login/login.pang" in page_url
            or "로그인이 필요" in body_text
            or (has_password_input and "coupang.com" in page_url)
        )

    async def _wait_for_visible_years(self, poll_count: int = 5) -> list[str]:
        for attempt in range(poll_count):
            years = await self._read_visible_years()
            if years:
                return years
            if attempt < poll_count - 1:
                await anyio.sleep(1)
        return []

    async def _collect_all_years(
        self,
        years: list[str],
        terminal: Terminal | None,
        cache: CoupangOrderList | None = None,
    ) -> tuple[list[CoupangOrderResult], list[list[int | str]]]:
        collected: list[CoupangOrderResult] = []
        failed_pages: list[list[int | str]] = []
        cached_orders_by_year = self._cacheable_orders_by_year(cache)
        for year in years:
            page_index = 0
            year_orders: list[CoupangOrderResult] = []
            cached_year_orders = cached_orders_by_year.get(year, [])
            while True:
                if terminal is not None:
                    terminal.info(f"{year}년 {page_index + 1}페이지 수집 중...")
                try:
                    page = await self._fetch_page_with_retry(year, page_index)
                except Exception:
                    failed_pages.append([year, page_index + 1])
                    break
                page_orders = [
                    self._build_order(order) for order in page["orderList"]
                ]
                cached_tail = self._cached_tail_for_page(
                    cached_year_orders,
                    len(year_orders),
                    page_orders,
                )
                if cached_tail is not None:
                    collected.extend(cached_tail)
                    year_orders.extend(cached_tail)
                    if terminal is not None:
                        terminal.cache(f"{year}년 나머지 주문은 캐시를 사용합니다.")
                    break

                collected.extend(page_orders)
                year_orders.extend(page_orders)
                pagination = page["orderPagination"]
                if not pagination["hasNext"]:
                    break
                page_index = pagination["nextPageIndex"]
        return collected, failed_pages

    async def _retry_failed_pages(self, terminal: Terminal | None) -> CoupangOrderList:
        previous = self._load_previous_order_list()
        if previous is None:
            return self._empty_payload(refresh=False)

        pages = self._normalize_failed_pages(previous.meta.failedPages)
        if not pages:
            summary = self._summarize_changes(previous.orders, previous.orders)
            return self._build_payload(
                previous.meta.years,
                [],
                False,
                previous.orders,
                summary,
            )

        collected, failed_pages = await self._collect_failed_pages(pages, terminal)
        orders = self._merge_orders(previous.orders, collected)
        summary = self._summarize_changes(previous.orders, orders)
        return self._build_payload(
            previous.meta.years,
            failed_pages,
            False,
            orders,
            summary,
        )

    async def _collect_failed_pages(
        self,
        pages: list[tuple[str, int]],
        terminal: Terminal | None,
    ) -> tuple[list[CoupangOrderResult], list[list[int | str]]]:
        collected: list[CoupangOrderResult] = []
        failed_pages: list[list[int | str]] = []
        for year, page_number in pages:
            if terminal is not None:
                terminal.info(f"{year}년 {page_number}페이지 재수집 중...")
            try:
                page = await self._fetch_page_with_retry(year, page_number - 1)
            except Exception:
                failed_pages.append([year, page_number])
                continue
            collected.extend(self._build_order(order) for order in page["orderList"])
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
                await anyio.sleep(1)
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
                    await anyio.sleep(1)
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
            provider=self.provider,
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
                            productUrl=self._build_product_url(product),
                        )
                        for product in group.get("productList", [])
                    ],
                )
                for group in data.get("deliveryGroupList", [])
            ],
        )

    def _build_product_url(self, product: dict[str, Any]) -> str:
        product_id = product.get("productId")
        item_id = product.get("itemId")
        vendor_item_id = product.get("vendorItemId")
        if product_id is None or item_id is None or vendor_item_id is None:
            return ""

        query = urlencode(
            {
                "itemId": str(item_id),
                "vendorItemId": str(vendor_item_id),
            }
        )
        return f"https://www.coupang.com/vp/products/{product_id}?{query}"

    def _read_message(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        message = value.get("message")
        return str(message) if message is not None else None

    def _emit_order_result(
        self,
        terminal: Terminal | None,
        payload: CoupangOrderList,
    ) -> None:
        if terminal is None:
            return

        message = format_coupang_order_list_message(payload)
        if payload.meta.failedPages:
            terminal.warn(message)
            return
        terminal.success(message)

    def _order_sync_result(
        self,
        payload: CoupangOrderList,
        request: OrderSyncRequest,
        metadata: ResultMetadata = EMPTY_METADATA,
    ) -> OrderSyncResult:
        if payload.meta.failedPages:
            metadata = ResultMetadata(
                error_code="partial_order_collection_failed",
                retryable=True,
                next_tools=("order_sync",),
            )
        return OrderSyncResult(
            success=metadata.error_code == "",
            provider=self.provider.value,
            message=format_coupang_order_list_message(payload),
            start_date=request.start_date,
            end_date=request.end_date,
            collected_orders=len(payload.orders),
            total_orders=payload.meta.summary.totalOrders,
            payload=payload,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _browser_closed_order_result(self, payload: CoupangOrderList, request: OrderSyncRequest) -> OrderSyncResult:
        return OrderSyncResult(
            success=False,
            provider=self.provider.value,
            message="브라우저가 닫혀 주문 수집을 완료하지 못했습니다.",
            start_date=request.start_date,
            end_date=request.end_date,
            payload=payload,
            error_code=BROWSER_CLOSED_METADATA.error_code,
            retryable=BROWSER_CLOSED_METADATA.retryable,
            next_tools=BROWSER_CLOSED_METADATA.next_tools,
        )

    def _not_logged_in_order_result(self, payload: CoupangOrderList) -> OrderSyncResult:
        return OrderSyncResult(
            success=False,
            provider=self.provider.value,
            message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
            payload=payload,
            error_code=LOGIN_REQUIRED_METADATA.error_code,
            retryable=LOGIN_REQUIRED_METADATA.retryable,
            next_tools=LOGIN_REQUIRED_METADATA.next_tools,
        )

    def _sync_required_order_list_result(self, request: OrderListRequest) -> OrderListResult:
        return OrderListResult(
            success=False,
            provider=self.provider.value,
            message="저장된 주문 데이터가 없습니다. 먼저 주문 수집이 필요합니다.",
            start_date=request.start_date,
            end_date=request.end_date,
            count=0,
            total_count=0,
            has_more=False,
            next_cursor=None,
            orders=(),
            error_code="sync_required",
            retryable=False,
            next_tools=("order_sync",),
        )

    def _filter_orders(
        self,
        orders: list[CoupangOrderResult],
        start_date: str | None,
        end_date: str | None,
        status: str,
    ) -> list[CoupangOrderResult]:
        start = date.fromisoformat(start_date) if start_date is not None else None
        end = date.fromisoformat(end_date) if end_date is not None else None
        return [
            order
            for order in orders
            if self._order_matches_period(order, start, end) and self._order_matches_status(order, status)
        ]

    def _order_matches_period(
        self,
        order: CoupangOrderResult,
        start_date: date | None,
        end_date: date | None,
    ) -> bool:
        ordered_at = self._ordered_at_date(order)
        if ordered_at is None:
            return False
        if start_date is not None and ordered_at < start_date:
            return False
        if end_date is not None and ordered_at > end_date:
            return False
        return True

    def _order_matches_status(self, order: CoupangOrderResult, status: str) -> bool:
        if status == "all":
            return True
        return self._order_status(order) == status

    def _order_list_item(self, order: CoupangOrderResult) -> OrderListItem:
        return OrderListItem(
            order_id=str(order.orderId),
            ordered_at=self._ordered_at_date_text(order),
            status=self._order_status(order),
            title=order.title,
            amount=order.totalProductPrice,
        )

    def _order_failure_item(self, order: CoupangOrderResult) -> OrderFailureItem:
        return OrderFailureItem(
            order_id=str(order.orderId),
            ordered_at=self._ordered_at_date_text(order),
            failure_type=self._order_status(order),
            title=order.title,
        )

    def _order_detail_items(self, order: CoupangOrderResult) -> list[OrderDetailItem]:
        return [
            OrderDetailItem(
                vendor_item_id=str(product.vendorItemId),
                name=product.productName or product.vendorItemName,
                quantity=product.quantity,
                amount=product.combinedUnitPrice,
            )
            for group in order.deliveryGroupList
            for product in group.productList
        ]

    def _is_failure_order(self, order: CoupangOrderResult) -> bool:
        failure_markers = ("CANCEL", "RETURN", "EXCHANGE", "FAIL", "ERROR")
        return any(marker in self._order_status(order).upper() for marker in failure_markers)

    def _order_status(self, order: CoupangOrderResult) -> str:
        for group in order.deliveryGroupList:
            if group.invoiceStatus:
                return group.invoiceStatus
        return "unknown"

    def _ordered_at_date_text(self, order: CoupangOrderResult) -> str:
        ordered_at = self._ordered_at_date(order)
        return "" if ordered_at is None else ordered_at.isoformat()

    def _ordered_at_date(self, order: CoupangOrderResult) -> date | None:
        for divisor in (1000, 1):
            try:
                ordered_at = datetime.fromtimestamp(order.orderedAt / divisor).date()
            except (OSError, OverflowError, ValueError):
                continue
            if 2000 <= ordered_at.year <= 2100:
                return ordered_at
        return None

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
                provider=self.provider,
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

    def _normalize_failed_pages(
        self,
        failed_pages: list[list[int | str]],
    ) -> list[tuple[str, int]]:
        normalized: list[tuple[str, int]] = []
        seen: set[tuple[str, int]] = set()
        for year, page_number in failed_pages:
            page = int(page_number)
            if page < 1:
                continue
            key = (str(year), page)
            if key in seen:
                continue
            normalized.append(key)
            seen.add(key)
        return normalized

    def _merge_orders(
        self,
        previous_orders: list[CoupangOrderResult],
        current_orders: list[CoupangOrderResult],
    ) -> list[CoupangOrderResult]:
        current_by_id = {order.orderId: order for order in current_orders}
        merged: list[CoupangOrderResult] = []
        for order in previous_orders:
            merged.append(current_by_id.pop(order.orderId, order))
        merged.extend(current_by_id.values())
        return merged

    def _cacheable_orders_by_year(
        self,
        cache: CoupangOrderList | None,
    ) -> dict[str, list[CoupangOrderResult]]:
        if cache is None or cache.meta.failedPages:
            return {}

        orders_by_year: dict[str, list[CoupangOrderResult]] = {}
        for order in cache.orders:
            year = self._ordered_at_year(order)
            if year is None:
                return {}
            orders_by_year.setdefault(year, []).append(order)
        return orders_by_year

    def _ordered_at_year(self, order: CoupangOrderResult) -> str | None:
        for divisor in (1000, 1):
            try:
                ordered_at = datetime.fromtimestamp(order.orderedAt / divisor)
            except (OSError, OverflowError, ValueError):
                continue
            if 2000 <= ordered_at.year <= 2100:
                return str(ordered_at.year)
        return None

    def _cached_tail_for_page(
        self,
        cached_orders: list[CoupangOrderResult],
        offset: int,
        page_orders: list[CoupangOrderResult],
    ) -> list[CoupangOrderResult] | None:
        if not cached_orders or not page_orders:
            return None

        page_size = len(page_orders)
        cached_page = cached_orders[offset : offset + page_size]
        if self._orders_match(cached_page, page_orders):
            return cached_orders[offset:]
        return None

    def _orders_match(
        self,
        left: list[CoupangOrderResult],
        right: list[CoupangOrderResult],
    ) -> bool:
        if [order.orderId for order in left] != [order.orderId for order in right]:
            return False
        return self._item_map(left) == self._item_map(right)

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
                        "product": {
                            "vendorItemId": product.vendorItemId,
                            "vendorItemName": product.vendorItemName,
                            "productName": product.productName,
                            "quantity": product.quantity,
                            "unitPrice": product.unitPrice,
                            "discountedUnitPrice": product.discountedUnitPrice,
                            "combinedUnitPrice": product.combinedUnitPrice,
                            "imagePath": product.imagePath,
                        },
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
