"""쿠팡 리뷰 작성 가능 목록 조회와 리뷰 업로드 흐름을 처리합니다."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab
from k_commerce_cli.services.store import ProviderStore
from .type import (
    ListReviewableResult,
    ReviewUploadRequest,
    ReviewUploadResult,
    ReviewableItem,
)
from .state import CoupangReviewState, REVIEW_STATE_MESSAGES, review_state_message
from .utils import build_review_register_url, format_reviewable_list

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_REVIEWABLE_URL = "https://my.coupang.com/productreview/reviewable"
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = (
    'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
)


@dataclass(frozen=True)
class _ReviewUploadBrowserResult:
    state: str
    message: str | None = None


@dataclass(frozen=True)
class _ReviewableItemData:
    product_id: str
    product_name: str
    delivery_date: str
    completed_order_vendor_item_id: str
    vendor_item_id: str
    review_url: str


@dataclass(frozen=True)
class _ListReviewableBrowserResult:
    state: str
    items: tuple[_ReviewableItemData, ...] = ()
    message: str | None = None


def deserialize_evaluate_result(value: object) -> object:
    """브라우저 evaluate 결과를 일반 Python 객체로 변환합니다."""
    if isinstance(value, dict) and "type" in value and "value" in value:
        typed = str(value["type"])
        inner = value["value"]
        if typed == "object":
            return {
                str(pair[0]): deserialize_evaluate_result(pair[1])
                for pair in inner
                if isinstance(pair, list) and len(pair) == 2
            }
        if typed == "array":
            return [deserialize_evaluate_result(item) for item in inner]
        if typed == "null":
            return None
        if typed in {"string", "number", "boolean"}:
            return inner
        return inner

    if isinstance(value, list):
        if value and all(
            isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) for item in value
        ):
            return {item[0]: deserialize_evaluate_result(item[1]) for item in value}
        return [deserialize_evaluate_result(item) for item in value]

    if isinstance(value, dict):
        return {key: deserialize_evaluate_result(item) for key, item in value.items()}

    return value


class CoupangReviewService:
    def __init__(
        self,
        provider_name: str,
        store: ProviderStore,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.store = store
        self.terminal = terminal
        self.browser = browser
        self._browser_session: BrowserSession | None = None

    async def list_reviewable(
        self,
        *,
        print_result: bool = True,
    ) -> ListReviewableResult:
        """저장된 세션으로 쿠팡 리뷰 작성 가능 상품 목록을 조회합니다."""
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 작성 가능 목록을 조회합니다...")

        if not self.store.has_session():
            return self._emit_list_result(
                ListReviewableResult(
                    provider=self.provider_name,
                    success=False,
                    message=REVIEW_STATE_MESSAGES[CoupangReviewState.NOT_LOGGED_IN],
                    items=(),
                ),
                print_result=print_result,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_reviewable_items(self._browser_session)
            return self._emit_list_result(
                self._to_list_result(browser_result),
                print_result=print_result,
            )
        finally:
            await self._close_browser_session()

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        """선택한 주문 상품에 별점과 리뷰 본문을 업로드합니다."""
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 업로드를 시작합니다...")

        if not self.store.has_session():
            return self._emit_upload_result(
                self._failure_result(
                    request,
                    REVIEW_STATE_MESSAGES[CoupangReviewState.NOT_LOGGED_IN],
                )
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._upload_review_browser(
                self._browser_session,
                review_url=request.review_url,
                product_id=request.product_id,
                rating=request.rating,
                text=request.text,
            )
            return self._emit_upload_result(self._to_result(request, browser_result))
        finally:
            await self._close_browser_session()

    def _to_list_result(
        self,
        browser_result: _ListReviewableBrowserResult,
    ) -> ListReviewableResult:
        """브라우저 목록 조회 결과를 CLI 서비스 결과 타입으로 변환합니다."""
        if browser_result.state != CoupangReviewState.SUCCESS:
            message = browser_result.message or review_state_message(
                browser_result.state,
                fallback="리뷰 작성 가능 목록 조회에 실패했습니다.",
            )
            return ListReviewableResult(
                provider=self.provider_name,
                success=False,
                message=message,
                items=(),
            )

        items = tuple(
            ReviewableItem(
                index=index,
                product_id=item.product_id,
                product_name=item.product_name,
                delivery_date=item.delivery_date,
                completed_order_vendor_item_id=item.completed_order_vendor_item_id,
                vendor_item_id=item.vendor_item_id,
                review_url=item.review_url,
            )
            for index, item in enumerate(browser_result.items, start=1)
        )
        return ListReviewableResult(
            provider=self.provider_name,
            success=True,
            message=format_reviewable_list(items),
            items=items,
        )

    def _to_result(
        self,
        request: ReviewUploadRequest,
        browser_result: _ReviewUploadBrowserResult,
    ) -> ReviewUploadResult:
        """브라우저 업로드 결과를 CLI 서비스 결과 타입으로 변환합니다."""
        if browser_result.state == CoupangReviewState.SUCCESS:
            return ReviewUploadResult(
                provider=self.provider_name,
                success=True,
                message="쿠팡 리뷰 업로드 성공",
                order_id=request.order_id,
                product_id=request.product_id,
            )

        message = browser_result.message or review_state_message(
            browser_result.state,
            fallback="리뷰 업로드에 실패했습니다.",
        )
        return self._failure_result(request, message)

    def _failure_result(
        self,
        request: ReviewUploadRequest,
        message: str,
    ) -> ReviewUploadResult:
        """리뷰 업로드 실패 결과를 생성합니다."""
        return ReviewUploadResult(
            provider=self.provider_name,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
        )

    def _emit_list_result(
        self,
        result: ListReviewableResult,
        *,
        print_result: bool = True,
    ) -> ListReviewableResult:
        """목록 조회 결과를 필요하면 출력하고 실패 시 CLI를 중단합니다."""
        terminal = self.terminal
        if print_result and terminal is not None:
            terminal.echo(result.message)
        if not result.success:
            if terminal is not None:
                terminal.abort(result.message)
        return result

    def _emit_upload_result(self, result: ReviewUploadResult) -> ReviewUploadResult:
        """업로드 결과를 출력하고 실패 시 CLI를 중단합니다."""
        terminal = self.terminal
        if terminal is not None:
            terminal.echo(result.message)
        if not result.success:
            if terminal is not None:
                terminal.abort(result.message)
        return result

    async def _close_browser_session(self) -> None:
        """열려 있는 브라우저 세션을 닫고 내부 참조를 정리합니다."""
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    async def _open_home(self, session: BrowserSession) -> None:
        """쿠팡 홈 화면을 엽니다."""
        await session.tab.get(COUPANG_HOME_URL)

    async def _is_logged_in(self, tab: BrowserTab) -> bool:
        """현재 탭이 쿠팡 로그인 상태인지 확인합니다."""
        page_state = await self._read_login_state(tab)
        page_url = str(page_state["url"])
        if "login.coupang.com" in page_url:
            return False

        if "my.coupang.com" in page_url:
            evaluate = getattr(tab, "evaluate", None)
            if callable(evaluate):
                try:
                    result = await evaluate(
                        """
                        (() => {
                          const bodyText = document.body?.innerText || '';
                          if (
                            bodyText.includes('로그인') &&
                            bodyText.includes('회원가입') &&
                            !bodyText.includes('마이쿠팡')
                          ) {
                            return false;
                          }
                          return !bodyText.includes('로그인이 필요');
                        })()
                        """
                    )
                    if isinstance(result, bool):
                        return result
                except Exception:
                    pass
            return True

        return (not page_state["has_login_link"]) and page_state["has_mycoupang_link"]

    async def _evaluate_json(self, tab: BrowserTab, script: str) -> object | None:
        """브라우저에서 JavaScript를 실행하고 JSON 형태 결과를 읽습니다."""
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return None

        try:
            result = await evaluate(script)
        except Exception:
            return None

        return deserialize_evaluate_result(result)

    async def _open_review_register(self, session: BrowserSession, review_url: str) -> None:
        """지정한 리뷰 작성 페이지를 열고 로딩을 기다립니다."""
        await session.tab.get(review_url)
        await self._sleep_ms(2500)

    async def _open_reviewable_list(self, session: BrowserSession) -> None:
        """쿠팡 리뷰 작성 가능 목록 페이지를 열고 로딩을 기다립니다."""
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
        """목록 페이지를 스크롤하며 리뷰 작성 가능한 상품을 모두 수집합니다."""
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
        """현재 목록 화면의 DOM에서 리뷰 작성 가능 상품 정보를 추출합니다."""
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

    async def _scroll_page(self, tab: BrowserTab) -> None:
        """현재 페이지를 맨 아래로 스크롤합니다."""
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return

        with contextlib.suppress(Exception):
            await evaluate(
                """
                (() => {
                  window.scrollTo(0, document.documentElement.scrollHeight);
                })()
                """
            )

    async def _upload_review_browser(
        self,
        session: BrowserSession,
        *,
        review_url: str,
        product_id: str,
        rating: int,
        text: str,
    ) -> _ReviewUploadBrowserResult:
        """브라우저에서 리뷰 작성 페이지를 열고 리뷰 제출까지 수행합니다."""
        await self._open_home(session)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        await self._open_review_register(session, review_url)

        active_tab = self._active_tab(session)
        page_state = await self._read_review_register_state(active_tab, product_id)
        if page_state != CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=page_state)

        submitted = await self._submit_review_form(active_tab, rating, text)
        if not submitted:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUBMIT_FAILED)

        confirmation = await self._read_review_upload_confirmation(active_tab)
        if confirmation == CoupangReviewState.SUCCESS:
            return _ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)

        return _ReviewUploadBrowserResult(state=confirmation)

    async def _read_review_register_state(self, tab: BrowserTab, product_id: str) -> str:
        """리뷰 작성 페이지가 제출 가능한 상태인지 판별합니다."""
        product_id_literal = json.dumps(product_id, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const productId = {product_id_literal};
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

    async def _submit_review_form(self, tab: BrowserTab, rating: int, text: str) -> bool:
        """리뷰 작성 폼에 별점과 본문을 입력한 뒤 제출 버튼을 누릅니다."""
        rating_literal = json.dumps(rating)
        text_literal = json.dumps(text, ensure_ascii=False)
        result = await self._evaluate_json(
            tab,
            f"""
            (() => {{
              const rating = {rating_literal};
              const text = {text_literal};
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

              const textarea = document.querySelector(
                'textarea[name*="review"], textarea[placeholder*="리뷰"], textarea.review-content, textarea'
              );
              if (!textarea) return false;

              textarea.focus();
              textarea.value = text;
              textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
              textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));

              const submitButton = Array.from(
                document.querySelectorAll('button, input[type="submit"]')
              ).find((element) => {{
                const label = (element.textContent || element.value || '').replace(/\\s+/g, '');
                return (
                  label.includes('등록') ||
                  label.includes('작성완료') ||
                  label.includes('리뷰등록') ||
                  label.includes('제출')
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

    async def _read_review_upload_confirmation(self, tab: BrowserTab) -> str:
        """리뷰 제출 후 화면 문구를 읽어 업로드 결과 상태를 판단합니다."""
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

    async def _sleep_ms(self, timeout_ms: int) -> None:
        """밀리초 단위 대기 시간을 asyncio sleep으로 처리합니다."""
        await asyncio.sleep(timeout_ms / 1000)

    async def _safe_select(self, tab: BrowserTab, selector: str, timeout: int = 1):
        """선택자 조회를 브라우저 adapter에 위임합니다."""
        return await self.browser.select(tab, selector, timeout=timeout)

    def _active_tab(self, session: BrowserSession) -> BrowserTab:
        """브라우저 세션에서 쿠팡 페이지로 보이는 활성 탭을 고릅니다."""
        runtime = getattr(session, "browser", None)
        candidates: list[BrowserTab] = []
        if runtime is not None:
            tabs = getattr(runtime, "tabs", None)
            if isinstance(tabs, list):
                candidates.extend(reversed(tabs))

            main_tab = getattr(runtime, "main_tab", None)
            if main_tab is not None:
                candidates.append(main_tab)
        candidates.append(session.tab)

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if "coupang.com" in url:
                return candidate

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if url.startswith(("https://", "http://", "about:blank")):
                return candidate

        for candidate in candidates:
            if hasattr(candidate, "select"):
                return candidate

        return session.tab

    async def _read_login_state(self, tab: BrowserTab) -> dict[str, object]:
        """현재 탭의 URL과 로그인/마이쿠팡 링크 존재 여부를 읽습니다."""
        evaluate = getattr(tab, "evaluate", None)
        if callable(evaluate):
            try:
                result = await evaluate(
                    """
                    (() => ({
                      url: window.location.href,
                      has_login_link: document.querySelector('a[href*="login/login.pang"]') !== null,
                      has_mycoupang_link:
                        document.querySelector('a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]') !== null
                    }))()
                    """
                )
                if isinstance(result, dict):
                    return {
                        "url": str(result.get("url", "")),
                        "has_login_link": bool(result.get("has_login_link", False)),
                        "has_mycoupang_link": bool(result.get("has_mycoupang_link", False)),
                    }
            except Exception:
                pass

        page_url = getattr(tab, "url", "")
        login_link = await self._safe_select(tab, COUPANG_LOGIN_LINK_SELECTOR)
        my_coupang_link = await self._safe_select(tab, COUPANG_MYCOUPANG_SELECTOR)
        return {
            "url": page_url,
            "has_login_link": login_link is not None,
            "has_mycoupang_link": my_coupang_link is not None,
        }
