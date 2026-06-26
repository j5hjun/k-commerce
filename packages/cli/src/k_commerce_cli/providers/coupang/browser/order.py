from __future__ import annotations

from k_commerce_cli.types import OrderListEntry

COUPANG_ORDER_LIST_URL = "https://mc.coupang.com/ssr/desktop/order/list"
ORDER_EVALUATE_ATTEMPTS = 2


class CoupangOrderBrowser:
    async def open_order_list(self, session: object) -> None:
        await session.tab.get(COUPANG_ORDER_LIST_URL)

    async def read_order_page_state(self, tab: object) -> dict[str, object]:
        evaluate = getattr(tab, "evaluate", None)
        if callable(evaluate):
            try:
                result = await evaluate(
                    """
                    (() => {
                      const text = (document.body?.innerText || '').replace(/\\s+/g, ' ').trim();
                      const hasLoginPrompt =
                        document.querySelector('input[type="password"], input[name="password"], form[action*="login"]') !== null;
                      const hasOrderSignals =
                        document.querySelector(
                          '[data-testid*="order"], [class*="my-area-contents"], [class*="my-area-body"], [class*="order"], [id*="order"]'
                        ) !== null ||
                        /주문번호|배송중|배송완료|결제완료|취소|반품|교환/.test(text);
                      const hasEmptyState =
                        /주문 내역이 없|주문한 상품이 없|주문이 없습니다|구매 내역이 없/.test(text);
                      const hasLoadingIndicator =
                        document.querySelector('[aria-busy="true"], [class*="loading"], [class*="skeleton"], [class*="spinner"]') !== null;

                      return {
                        url: window.location.href,
                        ready: !hasLoadingIndicator && (hasOrderSignals || hasEmptyState),
                        has_login_prompt: hasLoginPrompt,
                        has_order_signals: hasOrderSignals,
                        has_empty_state: hasEmptyState,
                        has_loading_indicator: hasLoadingIndicator,
                      };
                    })()
                    """
                )
                decoded = self._decode_evaluate_value(result)
                if isinstance(decoded, dict):
                    return {
                        "url": str(decoded.get("url", "")),
                        "ready": bool(decoded.get("ready", False)),
                        "has_login_prompt": bool(decoded.get("has_login_prompt", False)),
                        "has_order_signals": bool(decoded.get("has_order_signals", False)),
                        "has_empty_state": bool(decoded.get("has_empty_state", False)),
                        "has_loading_indicator": bool(decoded.get("has_loading_indicator", False)),
                    }
            except Exception:
                pass

        page_url = str(getattr(tab, "url", ""))
        return {
            "url": page_url,
            "ready": False,
            "has_login_prompt": "login.coupang.com" in page_url,
            "has_order_signals": False,
            "has_empty_state": False,
            "has_loading_indicator": False,
        }

    async def read_visible_orders(self, tab: object) -> tuple[OrderListEntry, ...]:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return ()

        rows = None
        for _attempt in range(ORDER_EVALUATE_ATTEMPTS):
            try:
                rows = await evaluate(
                    """
                    (() => {
                      const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                      const actionPattern = /주문 상세보기|배송 조회|교환, 반품 신청|리뷰 작성하기|판매자 문의|장바구니 담기|이전|다음/;
                      const orderDatePattern = /^\\d{4}\\.\\s*\\d{1,2}\\.\\s*\\d{1,2}\\s*주문/;
                      const statusPattern = /(결제완료|상품준비중|배송중|배송완료|취소|반품|교환|배송시작)/;

                      const orderRoot = document.querySelector('[class*="my-area-contents"] > div');
                      const orderGroups = orderRoot
                        ? [...orderRoot.children].filter((node) => {
                            const text = normalize(node.innerText);
                            return orderDatePattern.test(text) && /주문 상세보기/.test(text);
                          })
                        : [];

                      const rows = [];
                      const seenRows = new Set();

                      const buildRow = (text, title, status, quantity, hasDetailLink) => ({
                        title: normalize(title),
                        quantity: quantity || '1',
                        status: status || '',
                        has_detail_link: hasDetailLink,
                        raw_text: normalize(text),
                      });

                      for (const group of orderGroups) {
                        const groupText = normalize(group.innerText);
                        const groupHeaderMatch = groupText.match(/^\\d{4}\\.\\s*\\d{1,2}\\.\\s*\\d{1,2}\\s*주문/);
                        const groupHeader = groupHeaderMatch ? groupHeaderMatch[0] : '';
                        const groupHasDetailLink = /주문 상세보기/.test(groupText);
                        const orderIdMatch = groupText.match(/(?:주문번호|Order\\s*No\\.?)[^0-9]*([0-9-]+)/i);
                        const itemNodes = [...group.querySelectorAll('tr, [class*="sc-5a139ee-0"], td')]
                          .filter((node) => {
                            const text = normalize(node.innerText);
                            return text && /장바구니 담기/.test(text);
                          });

                        if (itemNodes.length === 0) {
                          continue;
                        }

                        const seenItemTexts = new Set();
                        for (const itemNode of itemNodes) {
                          const text = normalize(itemNode.innerText);
                          if (!text || seenItemTexts.has(text)) continue;
                          seenItemTexts.add(text);

                          const statusMatch = text.match(statusPattern);
                          const quantityMatch = text.match(/(?:\\s|^)(\\d+)개(?:\\s|$)/);
                          const productLinks = [...itemNode.querySelectorAll('a')]
                            .map((el) => normalize(el.innerText))
                            .filter((linkText) => {
                              if (!linkText) return false;
                              if (actionPattern.test(linkText)) return false;
                              if (orderDatePattern.test(linkText)) return false;
                              if (/\\d{1,3}(,\\d{3})*\\s*원/.test(linkText)) return false;
                              return linkText.length >= 5;
                            });

                          const title = productLinks[0] || '';
                          if (!title) continue;

                          const row = buildRow(
                            `${groupHeader} ${text}`,
                            title,
                            statusMatch ? statusMatch[1].trim() : '',
                            quantityMatch ? quantityMatch[1] : '1',
                            groupHasDetailLink,
                          );
                          const rowKey = [
                            row.title,
                            row.quantity,
                            row.status,
                          ].join('|');
                          if (seenRows.has(rowKey)) continue;
                          seenRows.add(rowKey);

                          rows.push(
                            row
                          );
                        }
                      }

                      return rows;
                    })()
                    """
                )
                break
            except Exception:
                rows = None

        if not isinstance(rows, list):
            return ()

        orders: list[OrderListEntry] = []
        for row in rows:
            decoded_row = self._decode_evaluate_value(row)
            if not isinstance(decoded_row, dict):
                continue

            title = str(decoded_row.get("title", "")).strip()
            if not title:
                continue

            status = str(decoded_row.get("status", "")).strip()
            has_detail_link = bool(decoded_row.get("has_detail_link", False))
            raw_text = str(decoded_row.get("raw_text", title)).strip()
            if not self._looks_like_order_row(
                title=title,
                status=status,
                has_detail_link=has_detail_link,
                raw_text=raw_text,
            ):
                continue

            quantity_raw = decoded_row.get("quantity", 1)
            try:
                quantity = int(quantity_raw)
            except (TypeError, ValueError):
                quantity = 1

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

    def _decode_evaluate_value(self, value: object) -> object:
        if isinstance(value, dict) and set(value.keys()) == {"type", "value"}:
            return self._decode_evaluate_value(value["value"])

        if isinstance(value, list):
            if all(
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], str)
                for item in value
            ):
                return {
                    str(key): self._decode_evaluate_value(raw_value)
                    for key, raw_value in value
                }

            return [self._decode_evaluate_value(item) for item in value]

        return value


__all__ = ["COUPANG_ORDER_LIST_URL", "CoupangOrderBrowser"]
