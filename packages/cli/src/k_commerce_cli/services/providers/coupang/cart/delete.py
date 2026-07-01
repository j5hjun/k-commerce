from __future__ import annotations

import json

from k_commerce_cli.services.base import BrowserSession, BrowserTab
from k_commerce_cli.services.providers.coupang.cart.state import CoupangCartState
from k_commerce_cli.services.providers.coupang.cart.type import (
    CartDeleteRequest,
    _ListCartBrowserResult,
)
from k_commerce_cli.services.providers.coupang.cart.utils import COUPANG_CART_URL
from k_commerce_cli.services.providers.coupang.review.browser import CoupangReviewBrowser


class CoupangCartDelete(CoupangReviewBrowser):
    async def _delete_cart_item_browser(
        self,
        session: BrowserSession,
        request: CartDeleteRequest,
    ) -> _ListCartBrowserResult:
        page_state = await self._prepare_cart_delete_page(session)
        if page_state is not None:
            return page_state

        return await self._delete_cart_item_on_page(self._active_tab(session), request)

    async def _delete_cart_items_browser(
        self,
        session: BrowserSession,
        requests: tuple[CartDeleteRequest, ...],
    ) -> _ListCartBrowserResult:
        if not requests:
            return _ListCartBrowserResult(
                state=CoupangCartState.VALIDATION_ERROR,
                message="삭제할 상품을 선택해주세요.",
            )

        page_state = await self._prepare_cart_delete_page(session)
        if page_state is not None:
            return page_state

        active_tab = self._active_tab(session)
        for request in requests:
            result = await self._delete_cart_item_on_page(active_tab, request)
            if result.state != CoupangCartState.SUCCESS:
                return result

        return _ListCartBrowserResult(state=CoupangCartState.SUCCESS)

    async def _delete_cart_item_on_page(
        self,
        tab: BrowserTab,
        request: CartDeleteRequest,
    ) -> _ListCartBrowserResult:
        clicked = await self._click_cart_item_delete_button(tab, request)
        if clicked is None:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
        if not clicked:
            return _ListCartBrowserResult(state=CoupangCartState.ITEM_NOT_FOUND)

        confirmed = await self._confirm_cart_delete_dialog(tab)
        if confirmed is None:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
        if not confirmed:
            return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        await self._sleep_ms(1500)
        if await self._is_cart_item_still_present(tab, request):
            return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        return _ListCartBrowserResult(state=CoupangCartState.SUCCESS)

    async def _clear_cart_browser(self, session: BrowserSession) -> _ListCartBrowserResult:
        page_state = await self._prepare_cart_delete_page(session)
        if page_state is not None:
            return page_state

        active_tab = self._active_tab(session)
        selected_all = await self._select_all_cart_items(active_tab)
        if selected_all is None:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
        if not selected_all:
            return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        clicked = await self._click_cart_bulk_delete_button(active_tab)
        if clicked is None:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
        if not clicked:
            cleared = await self._click_cart_clear_all_button(active_tab)
            if cleared is None:
                return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
            if not cleared:
                return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        confirmed = await self._confirm_cart_delete_dialog(active_tab)
        if confirmed is None:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
        if not confirmed:
            return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        await self._sleep_ms(1500)
        if not await self._is_cart_empty(active_tab):
            return _ListCartBrowserResult(state=CoupangCartState.DELETE_FAILED)

        return _ListCartBrowserResult(state=CoupangCartState.SUCCESS)

    async def _prepare_cart_delete_page(
        self,
        session: BrowserSession,
    ) -> _ListCartBrowserResult | None:
        try:
            await session.tab.get(COUPANG_CART_URL)
        except Exception:
            return _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
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
                return _ListCartBrowserResult(
                    state=CoupangCartState.VALIDATION_ERROR,
                    message="장바구니에 담긴 상품이 없습니다.",
                )
            return None

        return _ListCartBrowserResult(state=CoupangCartState.PAGE_LOAD_FAILED)

    def _cart_request_literal(self, request: CartDeleteRequest) -> str:
        return json.dumps(
            {
                "productId": request.product_id,
                "vendorItemId": request.vendor_item_id,
                "itemId": request.item_id,
            },
            ensure_ascii=False,
        )

    def _cart_requests_literal(self, requests: tuple[CartDeleteRequest, ...]) -> str:
        return json.dumps(
            [
                {
                    "productId": request.product_id,
                    "vendorItemId": request.vendor_item_id,
                    "itemId": request.item_id,
                }
                for request in requests
            ],
            ensure_ascii=False,
        )

    async def _click_cart_item_delete_button(
        self,
        tab: BrowserTab,
        request: CartDeleteRequest,
    ) -> bool | None:
        request_literal = self._cart_request_literal(request)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const request = {request_literal};
              {self._CART_ITEM_MATCHING_HELPERS}
              const container = findRequestedItemContainer(request);
              if (!container) return false;
              const deleteButton = findRowDeleteButton(container);
              if (!deleteButton) return false;
              deleteButton.click();
              return true;
            }})()
            """,
        )
        page_state = await self._read_cart_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _select_all_cart_items(self, tab: BrowserTab) -> bool | None:
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              {self._CART_ITEM_MATCHING_HELPERS}
              const selectAll = findSelectAllControl();
              if (!selectAll) return false;
              if (!selectAll.checked) {{
                selectAll.click();
              }}
              return selectAll.checked === true;
            }})()
            """,
        )
        page_state = await self._read_cart_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _click_cart_bulk_delete_button(self, tab: BrowserTab) -> bool | None:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeCompact = (text) => (text || '').replace(/\\s+/g, '');
              const controls = Array.from(document.querySelectorAll('button, a, div, [role="button"]'));
              const button = controls.find((element) => {
                const label = normalizeCompact(element.textContent || '');
                return label === '선택삭제';
              });
              if (!button || typeof button.click !== 'function') return false;
              button.click();
              return true;
            })()
            """,
        )
        page_state = await self._read_cart_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _click_cart_clear_all_button(self, tab: BrowserTab) -> bool | None:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeCompact = (text) => (text || '').replace(/\\s+/g, '');
              const controls = Array.from(document.querySelectorAll('button, a, div, [role="button"]'));
              const button = controls.find((element) => {
                const label = normalizeCompact(element.textContent || '');
                return (
                  label === '전체삭제' ||
                  label.includes('품절판매종료상품전체삭제') ||
                  label.includes('장바구니비우기')
                );
              });
              if (!button || typeof button.click !== 'function') return false;
              button.click();
              return true;
            })()
            """,
        )
        page_state = await self._read_cart_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _confirm_cart_delete_dialog(self, tab: BrowserTab) -> bool | None:
        await self._sleep_ms(500)
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeCompact = (text) => (text || '').replace(/\\s+/g, '');
              const candidates = Array.from(
                document.querySelectorAll('button, a, div, [role="button"]')
              );
              const button = candidates.find((element) => {
                const label = normalizeCompact(element.textContent || '');
                const popup = element.closest('[class*="modal"], [class*="popup"], [class*="dialog"], [role="dialog"]');
                const popupText = normalizeCompact(popup?.innerText || document.body?.innerText || '');
                if (!popupText.includes('삭제')) return false;
                return label.includes('확인') || label.includes('삭제') || label.includes('예');
              });
              if (!button || typeof button.click !== 'function') return false;
              button.click();
              return true;
            })()
            """,
        )
        page_state = await self._read_cart_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _is_cart_item_still_present(
        self,
        tab: BrowserTab,
        request: CartDeleteRequest,
    ) -> bool:
        request_literal = self._cart_request_literal(request)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const request = {request_literal};
              {self._CART_ITEM_MATCHING_HELPERS}
              return Boolean(findRequestedItemContainer(request));
            }})()
            """,
        )
        return result is True

    async def _is_cart_empty(self, tab: BrowserTab) -> bool:
        page_state = await self._read_cart_page_state(tab)
        if page_state["has_empty_cart_message"]:
            return True
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              {self._CART_ITEM_MATCHING_HELPERS}
              return document.querySelectorAll('.cart-quantity-input, [data-component-id="quantity-input"] input').length === 0;
            }})()
            """,
        )
        return result is True

    _CART_ITEM_MATCHING_HELPERS = """
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const normalizeCompact = (text) => (text || '').replace(/\\s+/g, '');
              const readAttributes = (element) =>
                Array.from(element?.attributes || [])
                  .map((attribute) => `${attribute.name}=${attribute.value}`)
                  .join(' ');
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
              const matchesRequestedItem = (request, ids) => {
                if (request.vendorItemId) {
                  return String(ids.vendorItemId || '') === String(request.vendorItemId);
                }
                if (request.itemId) {
                  return String(ids.itemId || '') === String(request.itemId);
                }
                if (request.productId) {
                  return String(ids.productId || '') === String(request.productId);
                }
                return false;
              };
              const readItemIds = (container) => {
                const itemRoot = container.closest('[id^="item_"], [data-bundle-id]') || container;
                const link = (
                  itemRoot.querySelector('a[href*="/vp/products"][href*="vendorItemId"][href*="sourceType=CART"], a[href*="/products"][href*="vendorItemId"][href*="sourceType=CART"]') ||
                  itemRoot.querySelector('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]') ||
                  container.querySelector('a[href*="/vp/products"][href*="vendorItemId"], a[href*="/products"][href*="vendorItemId"]')
                );
                const href = link?.getAttribute?.('href') || link?.href || '';
                const bundleId =
                  itemRoot.getAttribute('data-bundle-id') ||
                  (itemRoot.id || '').replace(/^item_/, '') ||
                  '';
                return {
                  vendorItemId: (
                    itemRoot.getAttribute('data-vid') ||
                    findDataValue(itemRoot, ['data-vid', 'data-vendor-item-id', 'data-vendoritemid', 'vendor-item-id', 'vendorItemId']) ||
                    (href.match(/vendorItemId=(\\d+)/) || [])[1] ||
                    new URL(href || window.location.href).searchParams.get('vendorItemId') ||
                    findIdByPattern(itemRoot, ['vendorItemId', 'vendor-item-id', 'vendorItem'])
                  ),
                  productId: (
                    findDataValue(itemRoot, ['data-product-id', 'data-productid', 'product-id', 'productId']) ||
                    (href || '').match(/\\/products\\/(\\d+)/)?.[1] ||
                    findIdByPattern(itemRoot, ['productId', 'product-id'])
                  ),
                  itemId: (
                    bundleId ||
                    findDataValue(itemRoot, ['data-bundle-id', 'data-cart-item-id', 'data-item-id', 'cart-item-id', 'item-id', 'cartItemId']) ||
                    findIdByPattern(itemRoot, ['cartItemId', 'cart-item-id', 'itemId', 'item-id', 'bundleId', 'bundle-id'])
                  ),
                };
              };
              const findRequestedItemContainer = (request) => {
                const itemRoots = Array.from(
                  document.querySelectorAll('[id^="item_"][data-bundle-id], [data-bundle-id]')
                );
                for (const itemRoot of itemRoots) {
                  const ids = readItemIds(itemRoot);
                  if (matchesRequestedItem(request, ids)) return itemRoot;
                }

                const quantityInputs = Array.from(
                  document.querySelectorAll('.cart-quantity-input, [data-component-id="quantity-input"] input')
                );
                for (const input of quantityInputs) {
                  const container = findItemContainer(input);
                  const ids = readItemIds(container);
                  if (matchesRequestedItem(request, ids)) return container.closest('[id^="item_"], [data-bundle-id]') || container;
                }
                return null;
              };
              const findRowDeleteButton = (container) => {
                const itemRoot = container.closest('[id^="item_"], [data-bundle-id]') || container;
                return Array.from(itemRoot.querySelectorAll('div, button, a, [role="button"]')).find((element) => {
                  const label = normalizeCompact(element.textContent || '');
                  return (
                    label === '삭제' &&
                    !label.includes('선택삭제') &&
                    !label.includes('전체삭제')
                  );
                }) || null;
              };
              const findSelectAllControl = () => {
                const labels = Array.from(document.querySelectorAll('label'));
                const label = labels.find((element) => {
                  const text = normalizeText(element.textContent || '');
                  return text.includes('전체 선택') || text.includes('전체선택');
                });
                if (!label) return null;
                return label.querySelector('input[type="checkbox"]');
              };
    """
