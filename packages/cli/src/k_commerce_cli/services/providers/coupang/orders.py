from __future__ import annotations

import asyncio
from datetime import datetime
import inspect
from typing import Any
from urllib.parse import urlencode

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, Store
from k_commerce_cli.services.providers.coupang.types import (
    CoupangDeliveryTrackingEvent,
    CoupangDeliveryTrackingPayload,
    CoupangDeliveryTrackingResult,
    CoupangDeliveryGroup,
    CoupangOrderList,
    CoupangOrderListResult,
    CoupangOrderMeta,
    CoupangOrderProduct,
    CoupangOrderResult,
    CoupangOrderSummary,
)
from k_commerce_cli.services.types import ProviderName

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

    async def list_orders(
        self,
        refresh: bool = False,
        failed_only: bool = False,
    ) -> CoupangOrderListResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 주문 수집을 시작합니다...")
        previous = self._load_previous_order_list()
        if not refresh and not failed_only and previous is not None and not previous.meta.failedPages:
            if terminal is not None:
                terminal.cache("저장된 주문 스냅샷을 바로 불러옵니다.")
            self._emit_order_result(terminal, previous)
            return CoupangOrderListResult(
                message=format_coupang_order_list_message(previous),
                payload=previous,
            )
        if not self.store.has_session():
            if previous is not None:
                if terminal is not None:
                    terminal.warn("세션이 없어 기존 주문 스냅샷을 유지합니다.")
                self._emit_order_result(terminal, previous)
                return CoupangOrderListResult(
                    message=format_coupang_order_list_message(previous),
                    payload=previous,
                )
            payload = self._empty_payload(refresh=refresh)
            self._emit_order_result(terminal, payload)
            return CoupangOrderListResult(
                message=format_coupang_order_list_message(payload),
                payload=payload,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_order_list(self._browser_session)
            if failed_only:
                payload = await self._retry_failed_pages(terminal)
                self.store.write_orders(payload.to_dict())
                self._emit_order_result(terminal, payload)
                return CoupangOrderListResult(
                    message=format_coupang_order_list_message(payload),
                    payload=payload,
                )

            years = await self._wait_for_visible_years()
            if not years:
                if previous is not None:
                    if terminal is not None:
                        terminal.warn("주문 페이지를 읽지 못해 기존 주문 스냅샷을 유지합니다.")
                    self._emit_order_result(terminal, previous)
                    return CoupangOrderListResult(
                        message=format_coupang_order_list_message(previous),
                        payload=previous,
                    )
                payload = self._empty_payload(refresh=refresh)
                self._emit_order_result(terminal, payload)
                return CoupangOrderListResult(
                    message=format_coupang_order_list_message(payload),
                    payload=payload,
                )

            previous = None if refresh else previous
            if terminal is not None:
                terminal.info(f"수집 연도: {', '.join(years)}")
            orders, failed_pages = await self._collect_all_years(
                years,
                terminal,
                cache=previous,
            )
            previous_orders = [] if previous is None else previous.orders
            summary = self._summarize_changes(previous_orders, orders)
            payload = self._build_payload(years, failed_pages, refresh, orders, summary)
            self.store.write_orders(payload.to_dict())
            self._emit_order_result(terminal, payload)
            return CoupangOrderListResult(
                message=format_coupang_order_list_message(payload),
                payload=payload,
            )
        finally:
            await self._close_browser_session()

    async def get_delivery_tracking(
        self,
        order_id: int,
        shipment_box_id: str,
    ) -> CoupangDeliveryTrackingResult:
        cached_order = self._find_cached_order(order_id, shipment_box_id)
        if not self.store.has_session():
            raise RuntimeError("쿠팡 로그인 상태가 아닙니다")

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            await self._open_order_list(self._browser_session)
            page_match = await self._find_order_group_page(
                order_id=order_id,
                shipment_box_id=shipment_box_id,
                preferred_year=self._cached_order_year(cached_order),
            )
            if page_match is None:
                raise RuntimeError("해당 배송 그룹을 주문목록에서 찾지 못했습니다")

            group, visible_index = page_match
            if not group.hasTrackAction:
                raise RuntimeError("이 배송 그룹은 배송조회 버튼이 없습니다")
            clicked = await self._click_track_action(visible_index)
            if not clicked:
                raise RuntimeError("배송조회 버튼을 열지 못했습니다")

            raw_payload = await self._wait_for_tracking_payload()
            raw_lines = [
                self._visible_card_text(line)
                for line in raw_payload.get("rawLines", [])
                if self._visible_card_text(line)
            ]
            events = [
                CoupangDeliveryTrackingEvent(
                    time=self._visible_card_text(item.get("time")),
                    status=self._visible_card_text(item.get("status")) or "-",
                    description=self._visible_card_text(item.get("description")),
                    location=self._visible_card_text(item.get("location")),
                )
                for item in raw_payload.get("events", [])
                if isinstance(item, dict) and self._visible_card_text(item.get("status"))
            ]
            payload = CoupangDeliveryTrackingPayload(
                provider=self.provider,
                orderId=order_id,
                shipmentBoxId=shipment_box_id,
                invoiceNumber=group.invoiceNumber,
                displayStatus=group.displayStatus,
                courierName=self._visible_card_text(raw_payload.get("courierName")),
                trackingNumber=self._visible_card_text(raw_payload.get("trackingNumber")) or group.invoiceNumber,
                summary=self._visible_card_text(raw_payload.get("summary")) or group.pddMessage.get("message"),
                events=events,
                rawLines=raw_lines,
                collectedAt=datetime.now().astimezone().replace(microsecond=0).isoformat(),
            )
            return CoupangDeliveryTrackingResult(
                message="배송조회 정보를 가져왔습니다",
                payload=payload,
            )
        finally:
            await self._close_browser_session()

    def _load_previous_orders(self) -> list[CoupangOrderResult]:
        previous = self._load_previous_order_list()
        if previous is None:
            return []
        return previous.orders

    def _find_cached_order(
        self,
        order_id: int,
        shipment_box_id: str,
    ) -> tuple[CoupangOrderResult, CoupangDeliveryGroup] | None:
        for order in self._load_previous_orders():
            if order.orderId != order_id:
                continue
            for group in order.deliveryGroupList:
                if group.shipmentBoxId == shipment_box_id:
                    return order, group
        return None

    def _cached_order_year(
        self,
        cached_order: tuple[CoupangOrderResult, CoupangDeliveryGroup] | None,
    ) -> str | None:
        if cached_order is None:
            return None
        return self._ordered_at_year(cached_order[0])

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

    async def _find_order_group_page(
        self,
        *,
        order_id: int,
        shipment_box_id: str,
        preferred_year: str | None,
    ) -> tuple[CoupangDeliveryGroup, int] | None:
        years = await self._wait_for_visible_years()
        if not years:
            return None
        ordered_years = years[:]
        if preferred_year and preferred_year in ordered_years:
            ordered_years = [preferred_year, *[year for year in ordered_years if year != preferred_year]]

        for year in ordered_years:
            page_index = 0
            while True:
                page = await self._fetch_page_with_retry(year, page_index)
                visible_cards = page.get("_visibleDeliveryCards", [])
                visible_index = 0
                for order in page["orderList"]:
                    built_order, next_visible_index = self._build_order(
                        order,
                        visible_cards,
                        visible_index,
                    )
                    for group_offset, group in enumerate(built_order.deliveryGroupList):
                        if (
                            built_order.orderId == order_id
                            and group.shipmentBoxId == shipment_box_id
                        ):
                            return group, visible_index + group_offset
                    visible_index = next_visible_index
                pagination = page["orderPagination"]
                if not pagination["hasNext"]:
                    break
                page_index = pagination["nextPageIndex"]
        return None

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
                visible_cards = page.get("_visibleDeliveryCards", [])
                visible_index = 0
                page_orders: list[CoupangOrderResult] = []
                for order in page["orderList"]:
                    built_order, visible_index = self._build_order(
                        order,
                        visible_cards,
                        visible_index,
                    )
                    page_orders.append(built_order)
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
            visible_cards = page.get("_visibleDeliveryCards", [])
            visible_index = 0
            for order in page["orderList"]:
                built_order, visible_index = self._build_order(
                    order,
                    visible_cards,
                    visible_index,
                )
                collected.append(built_order)
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
                payload = await self._wait_for_order_page_payload()
                payload["_visibleDeliveryCards"] = await self._read_visible_delivery_cards()
                return payload
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

    async def _read_visible_delivery_cards(self) -> list[dict[str, Any]]:
        try:
            result = await self._evaluate(
                """
                (() => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const actionLabels = ['배송 조회', '교환, 반품 신청', '리뷰 작성하기'];
                  const productLinkSelector = 'a[href*="vendorItemId"], a[href*="/vp/products/"], a[href*="/ssr/sdp/link"]';
                  const statusLabels = [
                    ['주문 취소', '주문 취소'],
                    ['주문취소', '주문 취소'],
                    ['취소완료', '주문 취소'],
                    ['취소', '주문 취소'],
                    ['반품완료', '반품완료'],
                    ['교환완료', '교환완료'],
                    ['배송완료', '배송완료'],
                    ['배송중', '배송중'],
                    ['상품준비중', '상품준비중'],
                    ['주문접수', '주문접수'],
                    ['주문확인', '주문확인'],
                  ];
                  const statusText = (text) => {
                    const normalized = normalize(text);
                    const compact = normalized.replace(/\\s+/g, '');
                    for (const [label, canonical] of statusLabels) {
                      if (compact === label.replace(/\\s+/g, '')) {
                        return canonical;
                      }
                    }
                    return null;
                  };
                  const buttons = Array.from(document.querySelectorAll('button, a'));
                  const productLinks = Array.from(document.querySelectorAll(productLinkSelector));
                  const cardRoots = [];
                  const seen = new Set();

                  const findCardRoot = (node) => {
                    let current = node instanceof Element ? node : null;
                    let candidate = null;
                    while (current && current !== document.body) {
                      const text = normalize(current.textContent);
                      const productLinkCount = current.querySelectorAll(productLinkSelector).length;
                      const hasPrice = /\\d{1,3}(,\\d{3})*\\s*원/.test(text);
                      const actionCount = actionLabels.filter((label) => text.includes(label)).length;
                      const hasStatus = statusLabels.some(([label]) => text.replace(/\\s+/g, '').includes(label.replace(/\\s+/g, '')));
                      if (productLinkCount >= 1 && hasPrice && (actionCount >= 1 || hasStatus)) {
                        return current;
                      }
                      current = current.parentElement;
                    }
                    return candidate;
                  };

                  for (const node of [...productLinks, ...buttons]) {
                    const root = findCardRoot(node);
                    if (!root || seen.has(root)) {
                      continue;
                    }
                    seen.add(root);
                    cardRoots.push(root);
                  }

                  return cardRoots.map((root) => {
                    const rootText = normalize(root.textContent);
                    const descendants = Array.from(root.querySelectorAll('div, span, strong, em, p, h1, h2, h3, h4, h5, h6'));
                    const displayStatus = descendants
                      .map((node) => normalize(node.textContent))
                      .map(statusText)
                      .find(Boolean) || statusText(rootText);
                    const buttonTexts = buttons
                      .filter((button) => root.contains(button))
                      .map((button) => normalize(button.textContent));

                    return {
                      displayStatus,
                      hasTrackAction: buttonTexts.some((text) => text.includes('배송 조회')),
                      hasExchangeReturnAction: buttonTexts.some((text) => text.includes('교환, 반품 신청')),
                      hasWriteReviewAction: buttonTexts.some((text) => text.includes('리뷰 작성하기')),
                    };
                  });
                })()
                """
            )
        except Exception:
            return []
        return result if isinstance(result, list) else []

    async def _click_track_action(self, visible_index: int) -> bool:
        try:
            result = await self._evaluate(
                f"""
                (() => {{
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const actionLabels = ['배송 조회', '교환, 반품 신청', '리뷰 작성하기'];
                  const productLinkSelector = 'a[href*="vendorItemId"], a[href*="/vp/products/"], a[href*="/ssr/sdp/link"]';
                  const statusLabels = [
                    ['주문 취소', '주문 취소'],
                    ['주문취소', '주문 취소'],
                    ['취소완료', '주문 취소'],
                    ['취소', '주문 취소'],
                    ['반품완료', '반품완료'],
                    ['교환완료', '교환완료'],
                    ['배송완료', '배송완료'],
                    ['배송중', '배송중'],
                    ['상품준비중', '상품준비중'],
                    ['주문접수', '주문접수'],
                    ['주문확인', '주문확인'],
                  ];
                  const buttons = Array.from(document.querySelectorAll('button, a'));
                  const productLinks = Array.from(document.querySelectorAll(productLinkSelector));
                  const cardRoots = [];
                  const seen = new Set();

                  const findCardRoot = (node) => {{
                    let current = node instanceof Element ? node : null;
                    let candidate = null;
                    while (current && current !== document.body) {{
                      const text = normalize(current.textContent);
                      const productLinkCount = current.querySelectorAll(productLinkSelector).length;
                      const hasPrice = /\\d{{1,3}}(,\\d{{3}})*\\s*원/.test(text);
                      const actionCount = actionLabels.filter((label) => text.includes(label)).length;
                      const hasStatus = statusLabels.some(([label]) => text.replace(/\\s+/g, '').includes(label.replace(/\\s+/g, '')));
                      if (productLinkCount >= 1 && hasPrice && (actionCount >= 1 || hasStatus)) {{
                        return current;
                      }}
                      current = current.parentElement;
                    }}
                    return candidate;
                  }};

                  for (const node of [...productLinks, ...buttons]) {{
                    const root = findCardRoot(node);
                    if (!root || seen.has(root)) {{
                      continue;
                    }}
                    seen.add(root);
                    cardRoots.push(root);
                  }}

                  const root = cardRoots[{visible_index}];
                  if (!root) {{
                    return false;
                  }}
                  const trackButton = buttons.find((button) =>
                    root.contains(button) && normalize(button.textContent).includes('배송 조회')
                  );
                  if (!trackButton) {{
                    return false;
                  }}
                  trackButton.click();
                  return true;
                }})()
                """
            )
        except Exception:
            return False
        return bool(result)

    async def _wait_for_tracking_payload(self, poll_count: int = 10) -> dict[str, Any]:
        last_payload: dict[str, Any] | None = None
        for attempt in range(poll_count):
            payload = await self._read_tracking_payload()
            if payload.get("summary") or payload.get("events") or payload.get("trackingNumber"):
                return payload
            last_payload = payload
            if attempt < poll_count - 1:
                await asyncio.sleep(1)
        return last_payload or {}

    async def _read_tracking_payload(self) -> dict[str, Any]:
        try:
            result = await self._evaluate(
                """
                (() => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const candidates = Array.from(document.querySelectorAll('[role="dialog"], dialog, section, main, div'));
                  const roots = candidates
                    .map((node) => ({
                      node,
                      text: normalize(node.textContent),
                    }))
                    .filter(({ text }) =>
                      text &&
                      (
                        text.includes('배송 조회') ||
                        text.includes('배송조회') ||
                        text.includes('송장번호') ||
                        text.includes('운송장번호') ||
                        text.includes('택배사') ||
                        text.includes('배송상태')
                      )
                    )
                    .sort((left, right) => right.text.length - left.text.length);

                  const root = (roots[0] && roots[0].node) || document.body;

                  const lineSet = new Set();
                  const rawLines = normalize(root.textContent)
                    .split(/\\n+/)
                    .map((line) => normalize(line))
                    .filter((line) => {
                      if (!line || lineSet.has(line)) {
                        return false;
                      }
                      lineSet.add(line);
                      return true;
                    })
                    .slice(0, 80);

                  const findValueByLabels = (labels) => {
                    const nodes = Array.from(root.querySelectorAll('dt, dd, th, td, div, span, strong, p'));
                    for (const node of nodes) {
                      const text = normalize(node.textContent);
                      if (!text) {
                        continue;
                      }
                      for (const label of labels) {
                        if (text === label || text.startsWith(`${label} `) || text.startsWith(`${label}:`)) {
                          const siblingTexts = Array.from(node.parentElement?.children || [])
                            .filter((child) => child !== node)
                            .map((child) => normalize(child.textContent))
                            .filter(Boolean);
                          const combined = siblingTexts.join(' ');
                          if (combined) {
                            return combined;
                          }
                          const stripped = text.replace(label, '').replace(/^[:\\s-]+/, '').trim();
                          if (stripped) {
                            return stripped;
                          }
                        }
                      }
                    }
                    return null;
                  };

                  const summary = rawLines.find((line) =>
                    /(배송완료|배송중|집하|간선|배달|도착|출고|출발|취소|반품)/.test(line)
                  ) || null;
                  const courierName = findValueByLabels(['택배사', '배송업체', '배송사', '운송사']);
                  const trackingNumber = findValueByLabels(['송장번호', '운송장번호', '배송번호']);

                  const eventRoots = Array.from(root.querySelectorAll('tr, li, [role="listitem"], div, p'))
                    .map((node) => ({
                      node,
                      text: normalize(node.textContent),
                    }))
                    .filter(({ text }) =>
                      text &&
                      text.length <= 240 &&
                      (/(\\d{4}[./-]\\d{1,2}[./-]\\d{1,2})|(오전|오후|\\d{1,2}:\\d{2})/.test(text) ||
                        /(배송완료|배송중|집하|배달|도착|출발|간선|취소|반품)/.test(text))
                    );

                  const seenEvents = new Set();
                  const events = eventRoots.map(({ node, text }) => {
                    const children = Array.from(node.children || [])
                      .map((child) => normalize(child.textContent))
                      .filter(Boolean);
                    const pieces = children.length >= 2 ? children : text.split(/\\s{2,}/).filter(Boolean);
                    const time = pieces.find((value) =>
                      /(\\d{4}[./-]\\d{1,2}[./-]\\d{1,2})|(오전|오후|\\d{1,2}:\\d{2})/.test(value)
                    ) || null;
                    const status = pieces.find((value) =>
                      /(배송완료|배송중|집하|배달|도착|출발|간선|취소|반품)/.test(value)
                    ) || pieces[0] || text;
                    const location = pieces.find((value, index) =>
                      index > 0 &&
                      value !== time &&
                      value !== status &&
                      value.length <= 40
                    ) || null;
                    const description = pieces
                      .filter((value) => value !== time && value !== status && value !== location)
                      .join(' ') || null;
                    const key = [time || '', status, location || '', description || ''].join('|');
                    if (seenEvents.has(key)) {
                      return null;
                    }
                    seenEvents.add(key);
                    return { time, status, location, description };
                  }).filter(Boolean).slice(0, 20);

                  return {
                    summary,
                    courierName,
                    trackingNumber,
                    events,
                    rawLines,
                  };
                })()
                """
            )
        except Exception:
            return {}
        return result if isinstance(result, dict) else {}

    def _build_order(
        self,
        data: dict[str, Any],
        visible_cards: list[dict[str, Any]] | None = None,
        visible_index: int = 0,
    ) -> tuple[CoupangOrderResult, int]:
        delivery_groups: list[CoupangDeliveryGroup] = []
        current_index = visible_index
        for group in data.get("deliveryGroupList", []):
            visible_card = (
                visible_cards[current_index]
                if visible_cards is not None and current_index < len(visible_cards)
                else {}
            )
            delivery_groups.append(
                CoupangDeliveryGroup(
                    shipmentBoxId=str(group["shipmentBoxId"]),
                    invoiceNumber=str(group["invoiceNumber"]),
                    invoiceStatus=str(group["invoiceStatus"]),
                    pddMessage={"message": self._read_message(group.get("pddMessage"))},
                    displayStatus=self._visible_card_text(visible_card.get("displayStatus")),
                    hasTrackAction=bool(visible_card.get("hasTrackAction", False)),
                    hasExchangeReturnAction=bool(visible_card.get("hasExchangeReturnAction", False)),
                    hasWriteReviewAction=bool(visible_card.get("hasWriteReviewAction", False)),
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
            )
            current_index += 1
        return CoupangOrderResult(
            provider=self.provider,
            orderId=int(data["orderId"]),
            title=str(data["title"]),
            orderedAt=int(data["orderedAt"]),
            totalProductPrice=int(data["totalProductPrice"]),
            deliveryGroupList=delivery_groups,
        ), current_index

    def _visible_card_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

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
