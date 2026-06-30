from __future__ import annotations

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab
from k_commerce_cli.services.providers.coupang.cart.state import (
    CART_STATE_MESSAGES,
    CoupangCartState,
    cart_state_message,
)
from k_commerce_cli.services.providers.coupang.cart.type import (
    _CartItemData,
    _ListCartBrowserResult,
)
from k_commerce_cli.services.providers.coupang.cart.utils import (
    COUPANG_CART_URL,
    format_cart_list,
)
from k_commerce_cli.services.base import Store
from k_commerce_cli.services.providers.coupang.review.browser import CoupangReviewBrowser
from k_commerce_cli.services.types import CartItem, ListCartResult, ProviderName


class CoupangCartService(CoupangReviewBrowser):
    def __init__(
        self,
        provider: ProviderName,
        store: Store,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider = provider
        self.store = store
        self.terminal = terminal
        self.browser = browser
        self._browser_session: BrowserSession | None = None

    async def list_cart(self, *, print_result: bool = True) -> ListCartResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 장바구니 목록을 조회합니다...")

        if not self.store.has_session():
            return self._emit_list_result(
                ListCartResult(
                    provider=self.provider.value,
                    success=False,
                    message=CART_STATE_MESSAGES[CoupangCartState.NOT_LOGGED_IN],
                    items=(),
                ),
                print_result=print_result,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_cart_items(self._browser_session)
            return self._emit_list_result(
                self._to_list_result(browser_result),
                print_result=print_result,
            )
        finally:
            await self._close_browser_session()

    async def _list_cart_items(self, session: BrowserSession) -> _ListCartBrowserResult:
        await session.tab.get(COUPANG_CART_URL)
        await self._sleep_ms(2500)

        for _ in range(8):
            active_tab = self._active_tab(session)
            page_state = await self._read_cart_page_state(active_tab)
            if page_state["is_login_page"]:
                return _ListCartBrowserResult(state=CoupangCartState.NOT_LOGGED_IN)

            items = await self._scrape_cart_items(active_tab)
            if items:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=items)
            if page_state["has_empty_cart_message"]:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=())
            if page_state["has_cart_content"] and not page_state["is_blank"]:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=())

            await self._sleep_ms(1000)

        return _ListCartBrowserResult(state=CoupangCartState.PAGE_LOAD_FAILED)

    async def _read_cart_page_state(self, tab: BrowserTab) -> dict[str, bool]:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const bodyText = (document.body?.innerText || '').replace(/\\s+/g, ' ').trim();
              const url = window.location.href;
              return {
                is_login_page:
                  url.includes('login.coupang.com') ||
                  bodyText.includes('로그인이 필요') ||
                  (bodyText.includes('로그인') && bodyText.includes('회원가입') && !bodyText.includes('장바구니')),
                is_blank: bodyText.length === 0,
                has_empty_cart_message:
                  bodyText.includes('장바구니에 담긴 상품이 없습니다') ||
                  bodyText.includes('장바구니가 비어'),
                has_cart_content:
                  bodyText.includes('장바구니') ||
                  document.querySelector('a[href*="/vp/products"][href*="vendorItemId"], .cart-quantity-input, [data-component-id="quantity-input"]') !== null
              };
            })()
            """,
        )
        if not isinstance(result, dict):
            return {
                "is_login_page": False,
                "is_blank": True,
                "has_empty_cart_message": False,
                "has_cart_content": False,
            }
        return {
            "is_login_page": bool(result.get("is_login_page", False)),
            "is_blank": bool(result.get("is_blank", False)),
            "has_empty_cart_message": bool(result.get("has_empty_cart_message", False)),
            "has_cart_content": bool(result.get("has_cart_content", False)),
        }

    async def _scrape_cart_items(self, tab: BrowserTab) -> tuple[_CartItemData, ...]:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const digits = (text) => String(text || '').replace(/[^0-9]/g, '');
              const formatWon = (value) => value ? `${Number(value).toLocaleString('ko-KR')}원` : '';
              const splitProductText = (text) => {
                const value = normalizeText(text);
                const name = normalizeText(value.split(/옵션:|삭제|한달구매|할인|품절임박/)[0]);
                const optionMatch = value.match(/옵션:\\s*(.*?)(?:삭제|한달구매|할인|품절임박|[0-9,]+\\s*원|$)/);
                return {
                  name,
                  option: normalizeText(optionMatch?.[1] || ''),
                };
              };
              const findDataValue = (container, names) => {
                for (const name of names) {
                  const direct = container?.getAttribute(name);
                  if (direct) return String(direct).trim();
                  const child = container?.querySelector(`[${name}]`);
                  const childValue = child?.getAttribute(name);
                  if (childValue) return String(childValue).trim();
                }
                return '';
              };
              const readAttributes = (element) =>
                Array.from(element?.attributes || [])
                  .map((attribute) => `${attribute.name}=${attribute.value}`)
                  .join(' ');
              const findIdByPattern = (container, names) => {
                const raw = [
                  readAttributes(container),
                  ...Array.from(container?.querySelectorAll('a[href], input, button, [onclick], [data-product-id], [data-vendor-item-id], [data-item-id]') || [])
                    .flatMap((element) => [
                      readAttributes(element),
                      element.getAttribute('href') || '',
                      element.getAttribute('onclick') || '',
                      element.value || '',
                    ]),
                ].filter(Boolean).join(' ');

                for (const name of names) {
                  const match = raw.match(new RegExp(`${name}["'=:\\\\s-]+([0-9]{4,})`, 'i'));
                  if (match) return match[1];
                }
                return '';
              };
              const readQuantity = (container) => {
                const quantityElement = (
                  container?.querySelector('input[name*="quantity" i], input[id*="quantity" i], input[class*="quantity" i], input[type="number"]') ||
                  container?.querySelector('[class*="quantity" i] input, [class*="qty" i] input')
                );
                const raw = quantityElement?.value || quantityElement?.getAttribute('value') || quantityElement?.textContent || '';
                const value = Number(digits(raw));
                return Number.isFinite(value) && value > 0 ? value : 1;
              };
              const readPrices = (container) => {
                const text = normalizeText(container?.innerText || '');
                const prices = [...text.matchAll(/[0-9,]+\\s*원/g)]
                  .map((match) => Number(match[0].replace(/[^0-9]/g, '')))
                  .filter((value) => Number.isFinite(value) && value > 0);
                const unique = [];
                for (const price of prices) {
                  if (unique[unique.length - 1] !== price) unique.push(price);
                }
                return unique;
              };
              const readUnitPrice = (container, quantity, totalPrice) => {
                const unitText = normalizeText(container?.innerText || '').match(/1개당\\s*([0-9,]+)\\s*원/);
                if (unitText) return `${unitText[1]}원`;
                if (quantity > 1 && totalPrice) return formatWon(Math.round(totalPrice / quantity));
                return formatWon(totalPrice);
              };
              const findItemContainer = (element) => {
                let current = element;
                for (let depth = 0; current && depth < 8; depth += 1) {
                  const text = normalizeText(current.innerText || '');
                  if (
                    current.querySelector?.('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]') &&
                    /[0-9,]+\\s*원/.test(text)
                  ) {
                    return current;
                  }
                  current = current.parentElement;
                }
                return element.closest('li, tr, article, section, div') || element;
              };
              const candidates = Array.from(
                document.querySelectorAll('.cart-quantity-input, [data-component-id="quantity-input"] input')
              )
                .map((quantityInput) => {
                  const container = findItemContainer(quantityInput);
                  const link = (
                    container.querySelector('a[href*="/vp/products"][href*="vendorItemId"][href*="sourceType=CART"], a[href*="/products"][href*="vendorItemId"][href*="sourceType=CART"]') ||
                    container.querySelector('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]')
                  );
                  return { link, container };
                })
                .filter((element) => {
                  const text = normalizeText(element?.container?.innerText || '');
                  return element.link && text && /[0-9]/.test(text) && !text.includes('장바구니 비우기');
                });
              const seen = new Set();
              const items = [];

              for (const candidate of candidates) {
                const container = candidate.container;
                const productLink = candidate.link;
                const productText = splitProductText(
                  productLink?.textContent ||
                  container.querySelector('[class*="name" i], [class*="title" i], strong')?.textContent ||
                  container.querySelector('img[alt]')?.getAttribute('alt') ||
                  ''
                );
                const productName = productText.name;
                if (!productName) continue;

                const vendorItemId = (
                  findDataValue(container, ['data-vendor-item-id', 'data-vendoritemid', 'vendor-item-id', 'vendorItemId']) ||
                  new URL(productLink?.href || window.location.href).searchParams.get('vendorItemId') ||
                  findIdByPattern(container, ['vendorItemId', 'vendor-item-id', 'vendorItem'])
                );
                const productId = (
                  findDataValue(container, ['data-product-id', 'data-productid', 'product-id', 'productId']) ||
                  (productLink?.href || '').match(/\\/products\\/(\\d+)/)?.[1] ||
                  findIdByPattern(container, ['productId', 'product-id'])
                );
                const itemId = (
                  findDataValue(container, ['data-cart-item-id', 'data-item-id', 'cart-item-id', 'item-id', 'cartItemId']) ||
                  findIdByPattern(container, ['cartItemId', 'cart-item-id', 'itemId', 'item-id'])
                );
                const dedupeKey = vendorItemId || itemId || productId || productName;
                if (seen.has(dedupeKey)) continue;
                seen.add(dedupeKey);

                const quantity = readQuantity(container);
                const prices = readPrices(container);
                const totalPriceValue = prices.length ? prices[prices.length - 1] : 0;
                const unitPrice = readUnitPrice(container, quantity, totalPriceValue);
                const totalPrice = formatWon(totalPriceValue) || unitPrice;
                const deliveryText = normalizeText(
                  container.querySelector('[class*="delivery" i], [class*="arrival" i], [class*="shipping" i]')?.textContent || ''
                );

                items.push({
                  product_name: productName,
                  option_text: productText.option,
                  quantity,
                  unit_price: unitPrice,
                  total_price: totalPrice,
                  product_id: productId,
                  vendor_item_id: vendorItemId,
                  item_id: itemId,
                  delivery_text: deliveryText,
                });
              }

              return items;
            })()
            """,
        )
        if not isinstance(result, list):
            return ()

        items: list[_CartItemData] = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            product_name = str(entry.get("product_name") or "").strip()
            if not product_name:
                continue
            items.append(
                _CartItemData(
                    product_name=product_name,
                    option_text=str(entry.get("option_text") or "").strip(),
                    quantity=self._normalize_quantity(entry.get("quantity")),
                    unit_price=str(entry.get("unit_price") or "").strip(),
                    total_price=str(entry.get("total_price") or "").strip(),
                    product_id=str(entry.get("product_id") or "").strip(),
                    vendor_item_id=str(entry.get("vendor_item_id") or "").strip(),
                    item_id=str(entry.get("item_id") or "").strip(),
                    delivery_text=str(entry.get("delivery_text") or "").strip(),
                )
            )

        return tuple(items)

    def _normalize_quantity(self, value: object) -> int:
        try:
            quantity = int(value or 1)
        except (TypeError, ValueError):
            return 1
        return max(1, quantity)

    def _to_list_result(self, browser_result: _ListCartBrowserResult) -> ListCartResult:
        if browser_result.state != CoupangCartState.SUCCESS:
            message = browser_result.message or cart_state_message(
                browser_result.state,
                fallback="장바구니 목록 조회에 실패했습니다.",
            )
            return ListCartResult(
                provider=self.provider.value,
                success=False,
                message=message,
                items=(),
            )

        items = tuple(
            CartItem(
                index=index,
                product_name=item.product_name,
                option_text=item.option_text,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                product_id=item.product_id,
                vendor_item_id=item.vendor_item_id,
                item_id=item.item_id,
                delivery_text=item.delivery_text,
            )
            for index, item in enumerate(browser_result.items, start=1)
        )
        return ListCartResult(
            provider=self.provider.value,
            success=True,
            message=format_cart_list(items),
            items=items,
        )

    def _emit_list_result(
        self,
        result: ListCartResult,
        *,
        print_result: bool = True,
    ) -> ListCartResult:
        terminal = self.terminal
        if print_result and terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result
