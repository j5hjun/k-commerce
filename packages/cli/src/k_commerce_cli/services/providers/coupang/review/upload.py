from __future__ import annotations

import json

from k_commerce_cli.services.base import BrowserSession, BrowserTab

from .browser import CoupangReviewBrowser
from .state import CoupangReviewState
from .type import (
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
    _ReviewableItemData,
)
from .utils import build_review_register_url

COUPANG_REVIEWABLE_URL = "https://my.coupang.com/productreview/reviewable"


class CoupangReviewUpload(CoupangReviewBrowser):
    async def _open_review_register(self, session: BrowserSession, review_url: str) -> None:
        await session.tab.get(review_url)
        await self._sleep_ms(2500)

    async def _open_reviewable_list(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_REVIEWABLE_URL)
        await self._sleep_ms(3000)

    async def _list_reviewable_items(
        self,
        session: BrowserSession,
        *,
        max_scroll_attempts: int = 50,
        stable_scroll_rounds: int = 3,
        min_scroll_attempts: int = 8,
    ) -> _ListReviewableBrowserResult:
        await self._open_reviewable_list(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        page_url = str(getattr(active_tab, "url", ""))
        if "login.coupang.com" in page_url:
            return _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        stable_rounds = 0
        previous_count = 0
        items: tuple[_ReviewableItemData, ...] = ()

        for attempt in range(max_scroll_attempts):
            items = await self._scrape_reviewable_items(active_tab)
            count = len(items)
            if count == previous_count and attempt >= min_scroll_attempts:
                stable_rounds += 1
                if stable_rounds >= stable_scroll_rounds:
                    break
            else:
                stable_rounds = 0
                previous_count = count

            await self._scroll_page(active_tab)
            await self._sleep_ms(800)

        return _ListReviewableBrowserResult(
            state=CoupangReviewState.SUCCESS,
            items=items,
        )

    async def _scrape_reviewable_items(self, tab: BrowserTab) -> tuple[_ReviewableItemData, ...]:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const items = [];
              const seen = new Set();
              const buttons = Array.from(
                document.querySelectorAll('button[data-reference], button.js_reviewWritableWriteBtn')
              );

              for (const button of buttons) {
                const raw = button.getAttribute('data-reference') || '';
                let parsed = {};
                try {
                  parsed = JSON.parse(raw);
                } catch {
                  continue;
                }

                const productId = String(parsed.productId || '');
                const completedOrderVendorItemId = String(
                  parsed.completedOrderVendorItemId || ''
                );
                const vendorItemId = String(parsed.vendorItemId || '');
                const deliveryDate = String(parsed.deliveryDate || '');
                if (!productId || !completedOrderVendorItemId) continue;

                const key = `${completedOrderVendorItemId}:${productId}`;
                if (seen.has(key)) continue;
                seen.add(key);

                let container = button.closest('li.my-review__writable__list');
                if (!container) continue;

                const titleElement = container.querySelector('.my-review__writable__content-title');
                const dateElement = container.querySelector('.my-review__writable__date');
                const productName = normalizeText(titleElement?.textContent || '');
                const dateText = normalizeText(dateElement?.textContent || '');
                const deliveryMatch = dateText.match(
                  /(\\d{4})[.\\-/](\\d{2})[.\\-/](\\d{2})/
                );
                const displayDeliveryDate = deliveryMatch
                  ? `${deliveryMatch[1]}-${deliveryMatch[2]}-${deliveryMatch[3]}`
                  : deliveryDate;

                items.push({
                  product_id: productId,
                  product_name: productName,
                  delivery_date: displayDeliveryDate || deliveryDate,
                  completed_order_vendor_item_id: completedOrderVendorItemId,
                  vendor_item_id: vendorItemId,
                });
              }

              return items;
            })()
            """,
        )
        if not isinstance(result, list):
            return ()

        items: list[_ReviewableItemData] = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            product_id = str(entry.get("product_id") or "").strip()
            completed_order_vendor_item_id = str(
                entry.get("completed_order_vendor_item_id") or ""
            ).strip()
            vendor_item_id = str(entry.get("vendor_item_id") or "").strip()
            delivery_date = str(entry.get("delivery_date") or "").strip()
            if not product_id or not completed_order_vendor_item_id or not vendor_item_id or not delivery_date:
                continue
            review_url = build_review_register_url(
                completed_order_vendor_item_id=completed_order_vendor_item_id,
                product_id=product_id,
                delivery_date=delivery_date,
                vendor_item_id=vendor_item_id,
            )
            items.append(
                _ReviewableItemData(
                    product_id=product_id,
                    product_name=str(entry.get("product_name") or "").strip(),
                    delivery_date=delivery_date,
                    completed_order_vendor_item_id=completed_order_vendor_item_id,
                    vendor_item_id=vendor_item_id,
                    review_url=review_url,
                )
            )

        return tuple(items)

    async def _upload_review_browser(
        self,
        session: BrowserSession,
        *,
        review_url: str,
        order_id: str,
        product_id: str,
        rating: int,
        text: str,
    ) -> _ReviewUploadBrowserResult:
        await self._open_home(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        await self._open_review_register(session, review_url)

        active_tab = self._active_tab(session)
        page_state = await self._read_review_register_state(active_tab, product_id, order_id)
        if page_state != CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=page_state)

        submitted = await self._submit_review_form(active_tab, rating, text)
        if not submitted:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUBMIT_FAILED)

        confirmation = await self._read_review_upload_confirmation(active_tab)
        if confirmation == CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)

        return _ReviewUploadBrowserResult(state=confirmation)

    async def _read_review_register_state(self, tab: BrowserTab, product_id: str, order_id: str) -> str:
        product_id_literal = json.dumps(product_id, ensure_ascii=False)
        order_id_literal = json.dumps(order_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const productId = {product_id_literal};
              const orderId = {order_id_literal};
              const url = window.location.href;
              if (url.includes('login.coupang.com')) {{
                return {{ state: 'not_logged_in' }};
              }}

              const bodyText = document.body?.innerText || '';
              if (
                bodyText.includes('접근할 수 없') ||
                bodyText.includes('페이지를 찾을 수 없') ||
                bodyText.includes('요청하신 페이지') ||
                bodyText.includes('존재하지 않')
              ) {{
                return {{ state: 'order_not_found' }};
              }}

              const params = new URL(url).searchParams;
              const pageProductId = params.get('productId') || '';
              const pageOrderId = params.get('completedOrderVendorItemId') || '';
              if (pageProductId && pageProductId !== productId) {{
                return {{ state: 'product_not_found' }};
              }}
              if (pageOrderId && pageOrderId !== orderId) {{
                return {{ state: 'order_not_found' }};
              }}

              const reviewForm = document.querySelector(
                'form.review-form, form[name*="review"], textarea[name*="review"], textarea[placeholder*="리뷰"], .review-write, .sdp-review, textarea'
              );
              if (reviewForm) {{
                return {{ state: 'success' }};
              }}

              const alreadyReviewed = Array.from(
                document.querySelectorAll('button, a, span, div')
              ).some((element) => {{
                const label = (element.textContent || '').replace(/\\s+/g, '');
                return (
                  label.includes('리뷰작성완료') ||
                  label.includes('작성완료') ||
                  label.includes('리뷰를작성했') ||
                  label.includes('이미리뷰')
                );
              }});
              if (alreadyReviewed) {{
                return {{ state: 'already_reviewed' }};
              }}

              const notReviewable = Array.from(
                document.querySelectorAll('button, a, span, div')
              ).some((element) => {{
                const label = (element.textContent || '').replace(/\\s+/g, '');
                return (
                  label.includes('리뷰작성불가') ||
                  label.includes('작성기간이지났')
                );
              }});
              if (notReviewable) {{
                return {{ state: 'not_reviewable' }};
              }}

              if (!bodyText.includes(productId)) {{
                return {{ state: 'product_not_found' }};
              }}

              return {{ state: 'not_reviewable' }};
            }})()
            """,
        )
        if isinstance(result, dict) and result.get("state"):
            return str(result["state"])

        return CoupangReviewState.NOT_REVIEWABLE

    async def _read_review_upload_confirmation(self, tab: BrowserTab) -> str:
        await self._sleep_ms(1500)
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const bodyText = document.body?.innerText || '';
              if (
                bodyText.includes('리뷰 등록이 완료') ||
                bodyText.includes('리뷰가 등록') ||
                bodyText.includes('리뷰 작성이 완료') ||
                bodyText.includes('소중한 리뷰')
              ) {
                return { state: 'success' };
              }
              if (bodyText.includes('이미 리뷰')) {
                return { state: 'already_reviewed' };
              }
              return { state: 'submit_failed' };
            })()
            """,
        )
        if isinstance(result, dict) and result.get("state"):
            return str(result["state"])

        return CoupangReviewState.SUBMIT_FAILED

    async def _submit_review_form(self, tab: BrowserTab, rating: int, text: str) -> bool:
        rating_literal = json.dumps(rating)
        text_literal = json.dumps(text, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const rating = {rating_literal};
              const text = {text_literal};
              const directStar = document.querySelector(
                `.js_reviewModifyStarBtn[value="${{rating}}"], .js_reviewWritableStarBtn[value="${{rating}}"]`
              );
              if (directStar && typeof directStar.click === 'function') {{
                directStar.click();
              }} else {{
                const starSelectors = [
                  '.rating-star',
                  '.review-rating button',
                  '.star-rating button',
                  '[class*="rating"] button',
                  '[class*="star"] button',
                ];
                let starContainer = null;
                for (const selector of starSelectors) {{
                  starContainer = document.querySelector(selector);
                  if (starContainer) break;
                }}

                if (starContainer) {{
                  const stars = starContainer.parentElement?.querySelectorAll('button, span, i') || [];
                  const targetIndex = Math.max(0, Math.min(stars.length - 1, rating - 1));
                  const targetStar = stars[targetIndex];
                  if (targetStar && typeof targetStar.click === 'function') {{
                    targetStar.click();
                  }}
                }}
              }}

              const textarea = document.querySelector(
                '.js_reviewModifyTextArea, .js_reviewWritableTextArea, textarea[name*="review"], textarea[placeholder*="리뷰"], textarea.review-content, textarea'
              );
              if (!textarea) return false;

              textarea.focus();
              textarea.value = text;
              textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
              textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));

              const submitButton =
                document.querySelector('.js_reviewModifySubmitBtn, .js_reviewWritableSubmitBtn') ||
                Array.from(document.querySelectorAll('button, input[type="submit"]')).find((element) => {{
                const label = (element.textContent || element.value || '').replace(/\\s+/g, '');
                return (
                  label.includes('등록') ||
                  label.includes('작성완료') ||
                  label.includes('리뷰등록') ||
                  label.includes('제출') ||
                  label.includes('완료')
                );
              }});
              if (!submitButton || typeof submitButton.click !== 'function') {{
                return false;
              }}

              submitButton.click();
              return true;
            }})()
            """,
        )
        if isinstance(result, bool):
            return result

        textarea = await self._safe_select(
            tab,
            'textarea[name*="review"], textarea[placeholder*="리뷰"], textarea.review-content, textarea',
            timeout=3,
        )
        submit_button = await self._safe_select(
            tab,
            'button[type="submit"], button.review-submit, button',
            timeout=3,
        )
        if textarea is None or submit_button is None:
            return False

        await textarea.send_keys(text)
        await submit_button.click()
        return True
