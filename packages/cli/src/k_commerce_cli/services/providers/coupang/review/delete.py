from __future__ import annotations

import json

from k_commerce_cli.services.base import BrowserSession, BrowserTab

from .browser import CoupangReviewBrowser
from .state import CoupangReviewState
from .type import _ReviewUploadBrowserResult


class CoupangReviewDelete(CoupangReviewBrowser):
    async def _delete_review_browser(
        self,
        session: BrowserSession,
        *,
        review_id: str,
    ) -> _ReviewUploadBrowserResult:
        await self._open_wrote_reviews(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        clicked = await self._click_delete_review_button(active_tab, review_id)
        if not clicked:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.REVIEW_NOT_FOUND)

        confirmed = await self._confirm_delete_review(active_tab)
        if not confirmed:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUBMIT_FAILED)

        confirmation = await self._read_review_delete_confirmation(active_tab, review_id)
        if confirmation == CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)

        return _ReviewUploadBrowserResult(state=confirmation)

    async def _click_delete_review_button(self, tab: BrowserTab, review_id: str) -> bool:
        review_id_literal = json.dumps(review_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const reviewId = {review_id_literal};
              const button = Array.from(
                document.querySelectorAll('.js_reviewWroteListDeleteBtn, [data-reviewid], [data-review-id]')
              ).find((element) => {{
                const elementReviewId =
                  element.getAttribute('data-reviewid') ||
                  element.getAttribute('data-review-id') ||
                  '';
                const label = (element.textContent || '').replace(/\\s+/g, '');
                return elementReviewId === reviewId && label.includes('삭제');
              }});
              if (!button || typeof button.click !== 'function') return false;
              button.click();
              return true;
            }})()
            """,
        )
        return result is True

    async def _confirm_delete_review(self, tab: BrowserTab) -> bool:
        await self._sleep_ms(500)
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const buttons = Array.from(
                document.querySelectorAll('.my-review__closable-popup .confirm-btn, .confirm-btn, button')
              );
              const button = buttons.find((element) => {
                const label = (element.textContent || '').replace(/\\s+/g, '');
                const popup = element.closest('.my-review__closable-popup, .my-modal, [class*="popup"]');
                const popupText = (popup?.innerText || '').replace(/\\s+/g, '');
                return label.includes('확인') && (
                  popupText.includes('삭제시복구나재등록이불가능합니다') ||
                  popupText.includes('정말삭제하시겠습니까') ||
                  popupText.includes('삭제')
                );
              });
              if (!button || typeof button.click !== 'function') return false;
              button.click();
              return true;
            })()
            """,
        )
        return result is True

    async def _read_review_delete_confirmation(self, tab: BrowserTab, review_id: str) -> str:
        await self._sleep_ms(1500)
        review_id_literal = json.dumps(review_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const reviewId = {review_id_literal};
              const bodyText = document.body?.innerText || '';
              if (
                bodyText.includes('구매후기가 삭제되었습니다') ||
                bodyText.includes('리뷰가 삭제') ||
                bodyText.includes('삭제되었습니다')
              ) {{
                return {{ state: 'success' }};
              }}

              const deleteButton = Array.from(
                document.querySelectorAll('.js_reviewWroteListDeleteBtn, [data-reviewid], [data-review-id]')
              ).find((element) => {{
                const elementReviewId =
                  element.getAttribute('data-reviewid') ||
                  element.getAttribute('data-review-id') ||
                  '';
                const label = (element.textContent || '').replace(/\\s+/g, '');
                return elementReviewId === reviewId && label.includes('삭제');
              }});
              if (
                window.location.href.includes('/productreview/wroteReviews') &&
                !deleteButton
              ) {{
                return {{ state: 'success' }};
              }}

              return {{ state: 'submit_failed' }};
            }})()
            """,
        )
        if isinstance(result, dict) and result.get("state"):
            return str(result["state"])

        return CoupangReviewState.SUBMIT_FAILED
