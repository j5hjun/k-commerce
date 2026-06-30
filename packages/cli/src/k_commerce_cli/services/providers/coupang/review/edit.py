from __future__ import annotations

import json

from k_commerce_cli.services.base import BrowserSession, BrowserTab

from .browser import CoupangReviewBrowser
from .state import CoupangReviewState
from .type import _ReviewUploadBrowserResult
from .utils import build_review_modify_url


class CoupangReviewEdit(CoupangReviewBrowser):
    async def _open_review_modify(self, session: BrowserSession, review_id: str) -> None:
        await session.tab.get(build_review_modify_url(review_id=review_id))
        await self._sleep_ms(2500)

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
