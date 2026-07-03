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
        try:
            await self._open_wrote_reviews(session)
        except Exception:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)

        active_tab = self._active_tab(session)
        page_state = await self._read_review_page_state(active_tab)
        if page_state["read_failed"]:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
        if not await self._is_logged_in(active_tab):
            return _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        clicked: bool | None = False
        for _ in range(30):
            clicked = await self._click_delete_review_button(active_tab, review_id)
            if clicked is None:
                return _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
            if clicked:
                break
            await self._scroll_page(active_tab)
            await self._sleep_ms(800)

        if not clicked:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.REVIEW_NOT_FOUND)

        confirmed = await self._confirm_delete_review(active_tab)
        if confirmed is None:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
        if not confirmed:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUBMIT_FAILED)

        confirmation = await self._read_review_delete_confirmation(active_tab, review_id)
        if confirmation == CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)

        return _ReviewUploadBrowserResult(state=confirmation)

    async def _click_delete_review_button(
        self,
        tab: BrowserTab,
        review_id: str,
    ) -> bool | None:
        review_id_literal = json.dumps(review_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const reviewId = {review_id_literal};
              const normalizeText = (text) => (text || '').replace(/\\s+/g, '');
              const clickIfPossible = (button) => {{
                if (!button || typeof button.click !== 'function') return false;
                button.click();
                return true;
              }};
              const isDeleteControl = (element) => {{
                const label = normalizeText(element.textContent || '');
                return (
                  element.classList.contains('js_reviewWroteListDeleteBtn') ||
                  label.includes('삭제')
                );
              }};
              const matchesReviewId = (element) => {{
                const elementReviewId =
                  element.getAttribute('data-reviewid') ||
                  element.getAttribute('data-review-id') ||
                  '';
                return elementReviewId === reviewId;
              }};

              const directButton = Array.from(
                document.querySelectorAll(
                  '.js_reviewWroteListDeleteBtn, [data-reviewid], [data-review-id], button, a'
                )
              ).find((element) => isDeleteControl(element) && matchesReviewId(element));
              if (clickIfPossible(directButton)) return true;

              const modifyCandidate = Array.from(
                document.querySelectorAll('.js_reviewWroteListModifyBtn, a, button')
              ).find((element) => {{
                const href = element.href || element.getAttribute('href') || '';
                const attrs = Array.from(element.attributes || [])
                  .map((attribute) => attribute.value)
                  .join(' ');
                const raw = [href, attrs, element.getAttribute('onclick') || ''].join(' ');
                return (
                  raw.includes(`/wroteReviews/${{reviewId}}/`) ||
                  raw.includes(`reviewId=${{reviewId}}`)
                );
              }});
              if (modifyCandidate) {{
                const container =
                  modifyCandidate.closest('li.my-review__wrote__list, li, article, section') ||
                  modifyCandidate.closest('[data-reviewid], [data-review-id]') ||
                  modifyCandidate.parentElement;
                const deleteButton = container
                  ? Array.from(
                      container.querySelectorAll(
                        '.js_reviewWroteListDeleteBtn, button, a, [role="button"]'
                      )
                    ).find((element) => isDeleteControl(element))
                  : null;
                if (clickIfPossible(deleteButton)) return true;
              }}

              return false;
            }})()
            """,
        )
        page_state = await self._read_review_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
        return result is True

    async def _confirm_delete_review(self, tab: BrowserTab) -> bool | None:
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
        page_state = await self._read_review_page_state(tab)
        if result is None and page_state["read_failed"]:
            return None
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
        page_state = await self._read_review_page_state(tab)
        if page_state["read_failed"]:
            return CoupangReviewState.BROWSER_CLOSED

        return CoupangReviewState.SUBMIT_FAILED
