from __future__ import annotations

import json

from k_commerce_cli.services.base import BrowserSession, BrowserTab

from .browser import CoupangReviewBrowser
from .state import CoupangReviewState
from .type import (
    _EditableReviewItemData,
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
)
from .utils import COUPANG_WROTE_REVIEWS_URL, build_review_modify_url


class CoupangReviewEdit(CoupangReviewBrowser):
    async def _open_review_modify(self, session: BrowserSession, review_id: str) -> None:
        await session.tab.get(build_review_modify_url(review_id=review_id))
        await self._sleep_ms(2500)

    async def _open_wrote_reviews(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_WROTE_REVIEWS_URL)
        await self._sleep_ms(3000)

    async def _list_editable_review_items(
        self,
        session: BrowserSession,
        *,
        max_scroll_attempts: int = 30,
        stable_scroll_rounds: int = 3,
        min_scroll_attempts: int = 3,
    ) -> _ListReviewableBrowserResult:
        await self._open_wrote_reviews(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        stable_rounds = 0
        previous_count = 0
        items: tuple[_EditableReviewItemData, ...] = ()

        for attempt in range(max_scroll_attempts):
            items = await self._scrape_editable_review_items(active_tab)
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

    async def _scrape_editable_review_items(
        self,
        tab: BrowserTab,
    ) -> tuple[_EditableReviewItemData, ...]:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const modifyUrlFromReviewId = (reviewId) =>
                `https://my.coupang.com/productreview/wroteReviews/${reviewId}/modify?page=1`;
              const readAttributes = (element) =>
                Array.from(element?.attributes || [])
                  .map((attribute) => `${attribute.name}=${attribute.value}`)
                  .join(' ');
              const findReviewId = (element, href) => {
                const raw = [
                  href,
                  element?.getAttribute('data-reviewid'),
                  element?.getAttribute('data-review-id'),
                  element?.getAttribute('data-review-no'),
                  element?.getAttribute('data-review-seq'),
                  element?.getAttribute('data-product-review-id'),
                  element?.getAttribute('review-id'),
                  element?.getAttribute('onclick'),
                  readAttributes(element),
                  readAttributes(
                    element?.closest('[data-reviewid], [data-review-id], [data-product-review-id], [data-review-no], [data-review-seq]')
                  ),
                ].filter(Boolean).join(' ');

                const pathMatch = raw.match(/wroteReviews\\/(\\d{5,})\\/modify/);
                if (pathMatch) return pathMatch[1];

                const namedMatch = raw.match(/review(?:Id|No|Seq|_id)?["'=:\\s-]+(\\d{5,})/i);
                if (namedMatch) return namedMatch[1];

                return '';
              };
              const findDataValue = (container, element, names) => {
                for (const name of names) {
                  const value =
                    container?.getAttribute(name) ||
                    element?.getAttribute(name) ||
                    container?.querySelector(`[${name}]`)?.getAttribute(name) ||
                    '';
                  if (value) return String(value).trim();
                }
                return '';
              };
              const candidates = Array.from(
                document.querySelectorAll(
                  '.js_reviewWroteListModifyBtn, a, button, [role="button"], [onclick], [data-reviewid], [data-review-id], [data-product-review-id], [data-review-no], [data-review-seq]'
                )
              ).filter((element) => {
                const href = element.href || element.getAttribute('href') || '';
                const label = normalizeText(element.textContent || element.getAttribute('aria-label') || '');
                return (
                  href.includes('/productreview/wroteReviews/') ||
                  href.includes('/modify') ||
                  label.includes('수정') ||
                  element.classList.contains('js_reviewWroteListModifyBtn') ||
                  element.hasAttribute('data-reviewid') ||
                  element.hasAttribute('data-review-id') ||
                  element.hasAttribute('data-product-review-id') ||
                  element.hasAttribute('data-review-no') ||
                  element.hasAttribute('data-review-seq')
                );
              });
              const items = [];
              const seen = new Set();

              for (const element of candidates) {
                const href = element.href || element.getAttribute('href') || '';
                const reviewId = findReviewId(element, href);
                if (!reviewId || seen.has(reviewId)) continue;
                seen.add(reviewId);

                const container = (
                  element.closest('li.my-review__wrote__list, li, article, section') ||
                  element.closest('[data-product-review-id], [data-reviewid], [data-review-id], [data-review-no], [data-review-seq]') ||
                  element.parentElement
                );
                const titleElement = (
                  container?.querySelector('.js_reviewWroteListProductTitle') ||
                  container?.querySelector('.my-review__wrote__item_name') ||
                  container?.querySelector('[data-product-id]') ||
                  container?.querySelector('[class*="product"], [class*="title"], [class*="name"], strong, h3, h4')
                );
                const containerText = normalizeText(container?.innerText || '');
                const productName = normalizeText(
                  titleElement?.textContent ||
                  container?.querySelector('img[alt]')?.getAttribute('alt') ||
                  ''
                );
                const reviewText = normalizeText(
                  container?.querySelector('.my-review__wrote__content pre')?.textContent ||
                  container?.querySelector('[class*="content"], [class*="text"], p')?.textContent ||
                  ''
                );
                const rating = container?.querySelectorAll('.wrote-list-rating-active').length || 0;
                const productId = findDataValue(container, element, [
                  'data-product-id',
                  'data-productid',
                  'product-id',
                ]);
                const orderId = findDataValue(container, element, [
                  'data-order-id',
                  'data-orderid',
                  'data-completed-order-vendor-item-id',
                  'completed-order-vendor-item-id',
                ]);

                items.push({
                  review_id: reviewId,
                  product_id: productId.trim(),
                  order_id: orderId.trim(),
                  product_name: productName || containerText,
                  rating,
                  review_text: reviewText,
                  modify_url: href || modifyUrlFromReviewId(reviewId),
                });
              }

              return items;
            })()
            """,
        )
        if not isinstance(result, list):
            return ()

        items: list[_EditableReviewItemData] = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            review_id = str(entry.get("review_id") or "").strip()
            modify_url = str(entry.get("modify_url") or "").strip()
            if not review_id:
                continue
            items.append(
                _EditableReviewItemData(
                    review_id=review_id,
                    product_id=str(entry.get("product_id") or "").strip(),
                    order_id=str(entry.get("order_id") or "").strip(),
                    product_name=str(entry.get("product_name") or "").strip(),
                    rating=int(entry.get("rating") or 0),
                    review_text=str(entry.get("review_text") or "").strip(),
                    modify_url=modify_url or build_review_modify_url(review_id=review_id),
                )
            )

        return tuple(items)

    async def _edit_review_browser(
        self,
        session: BrowserSession,
        *,
        order_id: str,
        product_id: str,
        review_id: str,
        rating: int,
        text: str,
    ) -> _ReviewUploadBrowserResult:
        await self._open_home(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        await self._open_review_modify(session, review_id)

        active_tab = self._active_tab(session)
        page_state = await self._read_review_edit_state(active_tab, product_id, order_id, review_id)
        if page_state != CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=page_state)

        submitted = await self._submit_review_form(active_tab, rating, text)
        if not submitted:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUBMIT_FAILED)

        confirmation = await self._read_review_edit_confirmation(active_tab)
        if confirmation == CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)

        return _ReviewUploadBrowserResult(state=confirmation)

    async def _read_review_edit_state(
        self,
        tab: BrowserTab,
        product_id: str,
        order_id: str,
        review_id: str,
    ) -> str:
        product_id_literal = json.dumps(product_id, ensure_ascii=False)
        order_id_literal = json.dumps(order_id, ensure_ascii=False)
        review_id_literal = json.dumps(review_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const productId = {product_id_literal};
              const orderId = {order_id_literal};
              const reviewId = {review_id_literal};
              const url = new URL(window.location.href);
              if (url.href.includes('login.coupang.com')) {{
                return {{ state: 'not_logged_in' }};
              }}

              const pathMatch = url.pathname.match(/wroteReviews\\/(\\d+)\\/modify/);
              const pageReviewId = pathMatch ? pathMatch[1] : '';
              if (pageReviewId && pageReviewId !== reviewId) {{
                return {{ state: 'identifier_mismatch' }};
              }}

              const bodyText = document.body?.innerText || '';
              if (
                bodyText.includes('접근할 수 없') ||
                bodyText.includes('페이지를 찾을 수 없') ||
                bodyText.includes('존재하지 않') ||
                bodyText.includes('작성한 리뷰가 없')
              ) {{
                return {{ state: 'review_not_found' }};
              }}

              const readCandidateValues = (names) => {{
                const values = [];
                for (const name of names) {{
                  const paramValue = url.searchParams.get(name);
                  if (paramValue) values.push(paramValue);

                  for (const element of document.querySelectorAll(`[name="${{name}}"], [id="${{name}}"], [data-${{name}}]`)) {{
                    values.push(
                      element.value ||
                      element.getAttribute('value') ||
                      element.getAttribute(`data-${{name}}`) ||
                      element.textContent ||
                      ''
                    );
                  }}
                }}
                return values.map((value) => String(value).trim()).filter(Boolean);
              }};
              const hasMismatchedKnownValue = (expected, names) => {{
                if (!expected) return false;
                const values = readCandidateValues(names);
                return values.length > 0 && !values.includes(expected);
              }};

              if (hasMismatchedKnownValue(productId, ['productId', 'product-id', 'product_id'])) {{
                return {{ state: 'identifier_mismatch' }};
              }}
              if (
                hasMismatchedKnownValue(orderId, [
                  'completedOrderVendorItemId',
                  'completed-order-vendor-item-id',
                  'orderId',
                  'order-id',
                  'order_id',
                ])
              ) {{
                return {{ state: 'identifier_mismatch' }};
              }}

              const notEditable = Array.from(
                document.querySelectorAll('button, a, span, div, p')
              ).some((element) => {{
                const label = (element.textContent || '').replace(/\\s+/g, '');
                return (
                  label.includes('수정불가') ||
                  label.includes('수정할수없') ||
                  label.includes('수정기간이지났')
                );
              }});
              if (notEditable) {{
                return {{ state: 'not_editable' }};
              }}

              const reviewForm = document.querySelector(
                'form.review-form, form[name*="review"], textarea[name*="review"], textarea[placeholder*="리뷰"], .review-write, .sdp-review, textarea'
              );
              if (reviewForm) {{
                return {{ state: 'success' }};
              }}

              return {{ state: 'review_not_found' }};
            }})()
            """,
        )
        if isinstance(result, dict) and result.get("state"):
            return str(result["state"])

        return CoupangReviewState.REVIEW_NOT_FOUND

    async def _read_review_edit_confirmation(self, tab: BrowserTab) -> str:
        await self._sleep_ms(1500)
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const url = window.location.href;
              const bodyText = document.body?.innerText || '';
              if (
                bodyText.includes('구매후기가 수정되었습니다') ||
                bodyText.includes('리뷰 수정이 완료') ||
                bodyText.includes('리뷰가 수정') ||
                bodyText.includes('수정되었습니다')
              ) {
                return { state: 'success' };
              }
              if (
                url.includes('/productreview/wroteReviews') &&
                !url.includes('/modify') &&
                bodyText.includes('작성한 리뷰')
              ) {
                return { state: 'success' };
              }
              if (
                bodyText.includes('수정할 수 없') ||
                bodyText.includes('수정 불가')
              ) {
                return { state: 'not_editable' };
              }
              return { state: 'submit_failed' };
            })()
            """,
        )
        if isinstance(result, dict) and result.get("state"):
            return str(result["state"])

        return CoupangReviewState.SUBMIT_FAILED
