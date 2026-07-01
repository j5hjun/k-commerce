from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
from k_commerce_cli.services.types import (
    CartItem,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ListCartResult,
    ProviderName,
)

COUPANG_CART_LOGIN_URL = (
    "https://login.coupang.com/login/login.pang?"
    "rtnUrl=https://cart.coupang.com/cartView.pang"
)


class CoupangCartBrowserSession:
    def __init__(
        self,
        service: CoupangCartService,
        session: BrowserSession,
    ) -> None:
        self._service = service
        self._session = session

    async def list_cart(self) -> ListCartResult:
        return await self._service._list_cart_with_session(self._session)

    async def refresh_cart(self) -> ListCartResult:
        return await self._service._list_cart_with_session(
            self._session,
            reload_page=False,
            announce=False,
        )

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        return await self._service._update_cart_quantity_with_session(
            self._session,
            request,
        )


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

    async def list_cart(self) -> ListCartResult:
        async with self.cart_session() as cart_session:
            return await cart_session.list_cart()

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        async with self.cart_session() as cart_session:
            return await cart_session.update_cart_quantity(request)

    @asynccontextmanager
    async def cart_session(self) -> AsyncIterator[CoupangCartBrowserSession]:
        if self._browser_session is not None:
            yield CoupangCartBrowserSession(self, self._browser_session)
            return

        self._browser_session = await self.browser.launch(self.store.paths)
        try:
            yield CoupangCartBrowserSession(self, self._browser_session)
        finally:
            await self._close_browser_session()

    async def _list_cart_with_session(
        self,
        session: BrowserSession,
        *,
        reload_page: bool = True,
        announce: bool = True,
    ) -> ListCartResult:
        terminal = self.terminal
        if announce and terminal is not None:
            terminal.info("쿠팡 장바구니 목록을 조회합니다...")

        browser_result = await self._list_cart_items(session, reload_page=reload_page)
        return self._emit_list_result(self._to_list_result(browser_result))

    async def _update_cart_quantity_with_session(
        self,
        session: BrowserSession,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        validation_error = self._validate_quantity_update_request(request)
        if validation_error is not None:
            return self._emit_quantity_update_result(
                self._failure_quantity_update_result(request, validation_error)
            )

        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 장바구니 수량 수정을 시작합니다...")

        browser_result = await self._update_cart_quantity_browser(
            session,
            request,
        )
        return self._emit_quantity_update_result(
            self._to_quantity_update_result(request, browser_result)
        )

    async def _list_cart_items(
        self,
        session: BrowserSession,
        *,
        reload_page: bool = True,
    ) -> _ListCartBrowserResult:
        if reload_page:
            await session.tab.get(COUPANG_CART_URL)
            await self._sleep_ms(2500)

        for _ in range(8):
            active_tab = self._active_tab(session)
            page_state = await self._read_cart_page_state(active_tab)
            if page_state["read_failed"]:
                return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
            if page_state["is_login_page"]:
                login_state = await self._open_login_and_wait_for_cart(session, active_tab)
                if login_state != CoupangCartState.SUCCESS:
                    return _ListCartBrowserResult(state=login_state)
                continue

            items = await self._scrape_cart_items(active_tab)
            if items:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=items)
            if page_state["has_empty_cart_message"]:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=())
            if page_state["has_cart_content"] and not page_state["is_blank"]:
                return _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=())

            await self._sleep_ms(1000)

        return _ListCartBrowserResult(state=CoupangCartState.PAGE_LOAD_FAILED)

    async def _open_login_and_wait_for_cart(
        self,
        session: BrowserSession,
        tab: BrowserTab,
        *,
        poll_count: int = 300,
    ) -> str:
        terminal = self.terminal
        if terminal is not None:
            terminal.warn("쿠팡 로그인이 필요합니다. 브라우저에서 로그인해주세요...")

        try:
            await tab.get(COUPANG_CART_LOGIN_URL)
        except Exception:
            return CoupangCartState.BROWSER_CLOSED
        await self._sleep_ms(1000)

        read_failures = 0
        for _ in range(poll_count):
            active_tab = self._active_tab(session)
            page_state = await self._read_cart_page_state(active_tab)
            if page_state["read_failed"]:
                read_failures += 1
                if read_failures >= 3:
                    return CoupangCartState.BROWSER_CLOSED
                await self._sleep_ms(1000)
                continue

            read_failures = 0
            if page_state["is_login_page"] or page_state["is_blank"]:
                await self._sleep_ms(1000)
                continue

            if not page_state["has_cart_content"]:
                try:
                    await active_tab.get(COUPANG_CART_URL)
                except Exception:
                    return CoupangCartState.BROWSER_CLOSED
                await self._sleep_ms(1000)
                continue

            try:
                await self.browser.save_session(session, self.store.cookies_file)
                self.store.write_session_metadata({"login_method": "manual"})
            except Exception:
                return CoupangCartState.BROWSER_CLOSED
            if terminal is not None:
                terminal.info("쿠팡 로그인 상태입니다. 장바구니 작업을 계속합니다...")
            return CoupangCartState.SUCCESS

        return CoupangCartState.NOT_LOGGED_IN

    async def _read_cart_page_state(self, tab: BrowserTab) -> dict[str, bool]:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const bodyText = (document.body?.innerText || '').replace(/\\s+/g, ' ').trim();
              const url = window.location.href;
              const hasLoginLink =
                document.querySelector('a[href*="login/login.pang"], a[href*="login.coupang.com"]') !== null;
              const hasLoginForm =
                document.querySelector('input[name="email"], input#login-email-input, input[name="password"], input#login-password-input') !== null;
              const hasMyCoupangLink =
                document.querySelector('a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]') !== null;
              const hasCartItems =
                document.querySelector('a[href*="/vp/products"][href*="vendorItemId"], .cart-quantity-input, [data-component-id="quantity-input"]') !== null;
              const hasLoginOnlyCta =
                (bodyText.includes('로그인하기') || bodyText.includes('로그인 후')) && !hasMyCoupangLink && !hasCartItems;
              const hasLoggedOutCartMessage =
                bodyText.includes('로그인을 하시면, 장바구니에 보관된 상품을 확인하실 수 있습니다') ||
                bodyText.includes('로그인을 하시면') && bodyText.includes('장바구니에 보관된 상품');
              return {
                is_login_page:
                  url.includes('login.coupang.com') ||
                  bodyText.includes('로그인이 필요') ||
                  hasLoginForm ||
                  (hasLoginLink && !hasMyCoupangLink && !hasCartItems) ||
                  hasLoginOnlyCta ||
                  hasLoggedOutCartMessage,
                is_blank: bodyText.length === 0,
                has_empty_cart_message:
                  bodyText.includes('장바구니에 담은 상품이 없습니다') ||
                  bodyText.includes('장바구니에 담긴 상품이 없습니다') ||
                  bodyText.includes('장바구니가 비어'),
                has_cart_content:
                  bodyText.includes('장바구니') ||
                  hasCartItems
              };
            })()
            """,
        )
        if not isinstance(result, dict):
            return {
                "read_failed": True,
                "is_login_page": False,
                "is_blank": True,
                "has_empty_cart_message": False,
                "has_cart_content": False,
            }
        return {
            "read_failed": False,
            "is_login_page": bool(result.get("is_login_page", False)),
            "is_blank": bool(result.get("is_blank", False)),
            "has_empty_cart_message": bool(result.get("has_empty_cart_message", False)),
            "has_cart_content": bool(result.get("has_cart_content", False)),
        }

    async def _update_cart_quantity_browser(
        self,
        session: BrowserSession,
        request: CartQuantityUpdateRequest,
    ) -> _ListCartBrowserResult:
        await session.tab.get(COUPANG_CART_URL)
        await self._sleep_ms(2500)

        for _ in range(10):
            active_tab = self._active_tab(session)
            page_state = await self._read_cart_page_state(active_tab)
            if page_state["read_failed"]:
                return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
            if page_state["is_login_page"]:
                login_state = await self._open_login_and_wait_for_cart(session, active_tab)
                if login_state != CoupangCartState.SUCCESS:
                    return _ListCartBrowserResult(state=login_state)
                continue
            if page_state["is_blank"] or not page_state["has_cart_content"]:
                await self._sleep_ms(1000)
                continue
            if page_state["has_empty_cart_message"]:
                return _ListCartBrowserResult(state=CoupangCartState.ITEM_NOT_FOUND)

            result = await self._evaluate_json(
                active_tab,
                f"""
            (() => {{
              const request = {{
                productId: {request.product_id!r},
                vendorItemId: {request.vendor_item_id!r},
                itemId: {request.item_id!r},
                quantity: {request.quantity},
              }};
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const readAttributes = (element) =>
                Array.from(element?.attributes || [])
                  .map((attribute) => `${{attribute.name}}=${{attribute.value}}`)
                  .join(' ');
              const findDataValue = (container, names) => {{
                for (const name of names) {{
                  const direct = container?.getAttribute(name);
                  if (direct) return String(direct).trim();
                  const child = container?.querySelector(`[${{name}}]`);
                  const childValue = child?.getAttribute(name);
                  if (childValue) return String(childValue).trim();
                }}
                return '';
              }};
              const findIdByPattern = (container, names) => {{
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

                for (const name of names) {{
                  const match = raw.match(new RegExp(`${{name}}["'=:\\\\s-]+([0-9]{{4,}})`, 'i'));
                  if (match) return match[1];
                }}
                return '';
              }};
              const findItemContainer = (element) => {{
                let current = element;
                for (let depth = 0; current && depth < 8; depth += 1) {{
                  const text = normalizeText(current.innerText || '');
                  if (
                    current.querySelector?.('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]') &&
                    /[0-9,]+\\s*원/.test(text)
                  ) {{
                    return current;
                  }}
                  current = current.parentElement;
                }}
                return element.closest('li, tr, article, section, div') || element;
              }};
              const matchesRequestedItem = ({{ productId, vendorItemId, itemId }}) => {{
                if (request.vendorItemId) {{
                  return String(vendorItemId || '') === String(request.vendorItemId);
                }}
                if (request.itemId) {{
                  return String(itemId || '') === String(request.itemId);
                }}
                if (request.productId) {{
                  return String(productId || '') === String(request.productId);
                }}
                return false;
              }};
              const quantityInputs = Array.from(document.querySelectorAll('.cart-quantity-input, [data-component-id="quantity-input"] input'));
              if (quantityInputs.length === 0) {{
                return {{ state: 'page_load_failed' }};
              }}

              for (const input of quantityInputs) {{
                const container = findItemContainer(input);
                const link = (
                  container.querySelector('a[href*="/vp/products"][href*="vendorItemId"][href*="sourceType=CART"], a[href*="/products"][href*="vendorItemId"][href*="sourceType=CART"]') ||
                  container.querySelector('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]')
                );
                const href = link?.href || '';
                const vendorItemId = (
                  findDataValue(container, ['data-vendor-item-id', 'data-vendoritemid', 'vendor-item-id', 'vendorItemId']) ||
                  new URL(href || window.location.href).searchParams.get('vendorItemId') ||
                  findIdByPattern(container, ['vendorItemId', 'vendor-item-id', 'vendorItem'])
                );
                const productId = (
                  findDataValue(container, ['data-product-id', 'data-productid', 'product-id', 'productId']) ||
                  (href || '').match(/\\/products\\/(\\d+)/)?.[1] ||
                  findIdByPattern(container, ['productId', 'product-id'])
                );
                const itemId = (
                  findDataValue(container, ['data-cart-item-id', 'data-item-id', 'cart-item-id', 'item-id', 'cartItemId']) ||
                  findIdByPattern(container, ['cartItemId', 'cart-item-id', 'itemId', 'item-id'])
                );

                if (matchesRequestedItem({{ productId, vendorItemId, itemId }})) {{
                  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
                  input.focus();
                  if (setter) setter.call(input, String(request.quantity));
                  else input.value = String(request.quantity);
                  input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                  input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', bubbles: true }}));
                  input.dispatchEvent(new KeyboardEvent('keyup', {{ key: 'Enter', code: 'Enter', bubbles: true }}));
                  input.blur();
                  return {{ state: 'success' }};
                }}
              }}

              return {{ state: 'item_not_found' }};
            }})()
            """,
            )
            if isinstance(result, dict):
                state = str(result.get("state") or "")
                if state == CoupangCartState.SUCCESS:
                    await self._sleep_ms(1500)
                    notice = await self._read_cart_notice(active_tab)
                    return _ListCartBrowserResult(
                        state=CoupangCartState.SUCCESS,
                        message=notice,
                    )
                if state == CoupangCartState.ITEM_NOT_FOUND:
                    return _ListCartBrowserResult(state=CoupangCartState.ITEM_NOT_FOUND)

            await self._sleep_ms(1000)

        return _ListCartBrowserResult(state=CoupangCartState.PAGE_LOAD_FAILED)

    async def _read_cart_notice(self, tab: BrowserTab) -> str | None:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const bodyText = normalizeText(document.body?.innerText || '');
              const noticePatterns = [
                '최대 구매 가능한 수량으로 변경되었습니다.',
                '최대 구매 가능한 수량',
                '최대 구매 가능한',
                '구매 가능한 수량',
              ];
              if (bodyText.includes(noticePatterns[0])) {
                return noticePatterns[0];
              }
              for (const pattern of noticePatterns) {
                if (bodyText.includes(pattern)) {
                  const sentences = bodyText
                    .split(/(?<=[.!?。]|다\\.)\\s+/)
                    .map(normalizeText)
                    .filter(Boolean);
                  const sentence = sentences.find((entry) => entry.includes(pattern));
                  return sentence || pattern;
                }
              }
              return '';
            })()
            """,
        )
        notice = str(result or "").strip()
        return notice or None

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

    def _validate_quantity_update_request(
        self,
        request: CartQuantityUpdateRequest,
    ) -> str | None:
        if request.quantity < 1:
            return "수량은 1개 이상이어야 합니다."
        if not (request.product_id.strip() or request.vendor_item_id.strip() or request.item_id.strip()):
            return "장바구니 상품 식별자는 비어 있을 수 없습니다."
        return None

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

    def _to_quantity_update_result(
        self,
        request: CartQuantityUpdateRequest,
        browser_result: _ListCartBrowserResult,
    ) -> CartQuantityUpdateResult:
        if browser_result.state == CoupangCartState.SUCCESS:
            message = "쿠팡 장바구니 수량 수정 성공"
            if browser_result.message:
                message = f"{message}\n{browser_result.message}"
            return CartQuantityUpdateResult(
                provider=self.provider.value,
                success=True,
                message=message,
                quantity=request.quantity,
                product_id=request.product_id,
                vendor_item_id=request.vendor_item_id,
                item_id=request.item_id,
            )

        message = cart_state_message(
            browser_result.state,
            fallback="장바구니 수량 수정에 실패했습니다.",
        )
        return self._failure_quantity_update_result(request, message)

    def _failure_quantity_update_result(
        self,
        request: CartQuantityUpdateRequest,
        message: str,
    ) -> CartQuantityUpdateResult:
        return CartQuantityUpdateResult(
            provider=self.provider.value,
            success=False,
            message=message,
            quantity=request.quantity,
            product_id=request.product_id,
            vendor_item_id=request.vendor_item_id,
            item_id=request.item_id,
        )

    def _emit_list_result(
        self,
        result: ListCartResult,
    ) -> ListCartResult:
        terminal = self.terminal
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    def _emit_quantity_update_result(
        self,
        result: CartQuantityUpdateResult,
    ) -> CartQuantityUpdateResult:
        terminal = self.terminal
        if terminal is not None:
            if result.success:
                terminal.success(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result
