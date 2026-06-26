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
                        /로그인|회원가입|아이디|비밀번호/.test(text) &&
                        document.querySelector('input[type="password"], input[name="password"], form[action*="login"], a[href*="login"]') !== null;
                      const hasOrderSignals =
                        document.querySelector('[data-testid*="order"], [class*="order"], [id*="order"]') !== null ||
                        /주문번호|배송중|배송완료|결제완료|취소|반품|교환/.test(text);
                      const hasEmptyState =
                        /주문 내역이 없|주문한 상품이 없|주문이 없습니다|구매 내역이 없/.test(text);
                      const hasLoadingIndicator =
                        document.querySelector('[aria-busy="true"], [class*="loading"], [class*="skeleton"], [class*="spinner"]') !== null;

                      return {
                        url: window.location.href,
                        ready: hasOrderSignals || hasEmptyState,
                        has_login_prompt: hasLoginPrompt,
                        has_order_signals: hasOrderSignals,
                        has_empty_state: hasEmptyState,
                        has_loading_indicator: hasLoadingIndicator,
                      };
                    })()
                    """
                )
                if isinstance(result, dict):
                    return {
                        "url": str(result.get("url", "")),
                        "ready": bool(result.get("ready", False)),
                        "has_login_prompt": bool(result.get("has_login_prompt", False)),
                        "has_order_signals": bool(result.get("has_order_signals", False)),
                        "has_empty_state": bool(result.get("has_empty_state", False)),
                        "has_loading_indicator": bool(result.get("has_loading_indicator", False)),
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
                      const selectors = [
                        '[data-testid*="order"]',
                        'article',
                        'section',
                        'li',
                      ];
                      const seen = new Set();
                      const candidates = selectors.flatMap((selector) =>
                        [...document.querySelectorAll(selector)]
                      );

                      return candidates
                        .map((node) => {
                          const text = (node.innerText || '').replace(/\\s+/g, ' ').trim();
                          if (!text || seen.has(text)) return null;
                          seen.add(text);

                          const orderIdMatch = text.match(/(?:주문번호|Order\\s*No\\.?)[^0-9]*([0-9-]+)/i);
                          const quantityMatch = text.match(/(?:수량|구매수량)[^0-9]*([0-9]+)/);
                          const statusMatch = text.match(/(결제완료|상품준비중|배송중|배송완료|취소|반품|교환)/);
                          const titleNode =
                            node.querySelector('strong, h3, h4, [data-testid*="item-name"], [class*="name"]');
                          const title = (titleNode?.innerText || text).replace(/\\s+/g, ' ').trim();

                          return {
                            order_id: orderIdMatch ? orderIdMatch[1].trim() : '',
                            title,
                            quantity: quantityMatch ? quantityMatch[1] : '1',
                            status: statusMatch ? statusMatch[1].trim() : '',
                          };
                        })
                        .filter((row) => row && row.title);
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
            if not isinstance(row, dict):
                continue

            title = str(row.get("title", "")).strip()
            if not title:
                continue

            order_id = str(row.get("order_id", "")).strip()
            status = str(row.get("status", "")).strip()
            if not self._looks_like_order_row(title=title, order_id=order_id, status=status):
                continue

            quantity_raw = row.get("quantity", 1)
            try:
                quantity = int(quantity_raw)
            except (TypeError, ValueError):
                quantity = 1

            orders.append(
                OrderListEntry(
                    order_id=order_id,
                    title=title,
                    quantity=quantity,
                    status=status,
                )
            )

        return tuple(orders)

    def _looks_like_order_row(self, *, title: str, order_id: str, status: str) -> bool:
        if not title:
            return False

        has_order_id = any(character.isdigit() for character in order_id)
        has_known_status = status in {
            "결제완료",
            "상품준비중",
            "배송중",
            "배송완료",
            "취소",
            "반품",
            "교환",
        }
        return has_order_id or has_known_status


__all__ = ["COUPANG_ORDER_LIST_URL", "CoupangOrderBrowser"]
