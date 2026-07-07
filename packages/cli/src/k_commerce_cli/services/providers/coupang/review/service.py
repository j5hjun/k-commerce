from urllib.parse import quote

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab, Store
from k_commerce_cli.services.providers.coupang.result_metadata import (
    is_browser_closed_error,
    review_metadata,
)
from k_commerce_cli.services.types import (
    EditableReviewItem,
    ListEditableReviewsResult,
    ListReviewableResult,
    ProviderName,
    ReviewDeleteRequest,
    ReviewDeleteResult,
    ReviewEditRequest,
    ReviewEditResult,
    ReviewUploadRequest,
    ReviewUploadResult,
    ReviewableItem,
)

from .browser import deserialize_evaluate_result  # noqa: F401
from .delete import CoupangReviewDelete
from .edit import CoupangReviewEdit
from .state import CoupangReviewState, review_state_message
from .type import (
    _EditableReviewItemData,
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
    _ReviewableItemData,  # noqa: F401
)
from .upload import CoupangReviewUpload
from .utils import (
    COUPANG_REVIEW_REGISTER_URL,
    COUPANG_WROTE_REVIEWS_URL,
    build_review_modify_url,
    format_editable_review_list,
    format_reviewable_list,
)

COUPANG_REVIEWABLE_URL = "https://my.coupang.com/productreview/reviewable"
COUPANG_REVIEW_LOGIN_URL = "https://login.coupang.com/login/login.pang?rtnUrl={return_url}"


class CoupangReviewService(
    CoupangReviewUpload,
    CoupangReviewEdit,
    CoupangReviewDelete,
):
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

    async def list_reviewable(self) -> ListReviewableResult:
        """저장된 세션으로 쿠팡 리뷰 작성 가능 상품 목록을 조회합니다."""
        if not self.store.has_session():
            return self._to_list_result(
                _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)
            )
        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_reviewable_items(self._browser_session)
            if browser_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    COUPANG_REVIEWABLE_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    browser_result = await self._list_reviewable_items(self._browser_session)
                else:
                    browser_result = _ListReviewableBrowserResult(state=login_state)
            return self._to_list_result(browser_result)
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._to_list_result(
                _ListReviewableBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
            )
        finally:
            await self._close_browser_session()

    async def _open_wrote_reviews(self, session: BrowserSession) -> None:
        await session.tab.get(COUPANG_WROTE_REVIEWS_URL)
        await self._sleep_ms(3000)

    async def _open_login_and_wait_for_review(
        self,
        session: BrowserSession,
        return_url: str,
        *,
        poll_count: int = 300,
    ) -> str:
        terminal = self.terminal
        if terminal is not None:
            terminal.warn("쿠팡 로그인이 필요합니다. 브라우저에서 로그인해주세요...")

        active_tab = self._active_tab(session)
        if not await self._is_review_login_screen(active_tab):
            try:
                await active_tab.get(
                    COUPANG_REVIEW_LOGIN_URL.format(return_url=quote(return_url, safe=""))
                )
            except Exception:
                return CoupangReviewState.BROWSER_CLOSED
            await self._sleep_ms(1000)

        read_failures = 0
        for _ in range(poll_count):
            active_tab = self._active_tab(session)
            page_state = await self._read_review_page_state(active_tab)
            if page_state["read_failed"]:
                read_failures += 1
                if read_failures >= 3:
                    return CoupangReviewState.BROWSER_CLOSED
                await self._sleep_ms(1000)
                continue

            read_failures = 0
            page_url = str(page_state["url"])
            body_text = str(page_state["body_text"])
            if (
                not body_text.strip()
                or "login.coupang.com" in page_url
                or "로그인이 필요" in body_text
            ):
                await self._sleep_ms(1000)
                continue

            if await self._is_logged_in(active_tab):
                try:
                    await self.browser.save_session(session, self.store.cookies_file)
                    self.store.write_session_metadata({"login_method": "manual"})
                except Exception:
                    return CoupangReviewState.BROWSER_CLOSED
                if terminal is not None:
                    terminal.info("쿠팡 로그인 상태입니다. 리뷰 작업을 계속합니다...")
                return CoupangReviewState.SUCCESS

            await self._sleep_ms(1000)

        return CoupangReviewState.NOT_LOGGED_IN

    async def _list_editable_review_items(
        self,
        session: BrowserSession,
        *,
        max_scroll_attempts: int = 30,
        stable_scroll_rounds: int = 3,
        min_scroll_attempts: int = 3,
    ) -> _ListReviewableBrowserResult:
        try:
            await self._open_wrote_reviews(session)
        except Exception:
            return _ListReviewableBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)

        active_tab = self._active_tab(session)
        page_state = await self._read_review_page_state(active_tab)
        if page_state["read_failed"]:
            return _ListReviewableBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
        if not await self._is_logged_in(active_tab):
            return _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)

        stable_rounds = 0
        previous_count = 0
        items: tuple[_EditableReviewItemData, ...] = ()

        for attempt in range(max_scroll_attempts):
            items = await self._scrape_editable_review_items(active_tab)
            if items is None:
                return _ListReviewableBrowserResult(
                    state=CoupangReviewState.BROWSER_CLOSED
                )
            count = len(items)
            if count == previous_count and attempt >= min_scroll_attempts:
                if await self._is_page_scrolled_to_bottom(active_tab):
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
    ) -> tuple[_EditableReviewItemData, ...] | None:
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
              const buildItem = (container, element, href, reviewId) => {
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
                return {
                  review_id: reviewId,
                  product_id: productId.trim(),
                  order_id: orderId.trim(),
                  product_name: productName || containerText,
                  rating,
                  review_text: reviewText,
                  modify_url: href || modifyUrlFromReviewId(reviewId),
                };
              };
              const items = [];
              const seen = new Set();
              const listContainers = Array.from(
                document.querySelectorAll(
                  'li.my-review__wrote__list, .my-review__wrote__list > li, li[class*="my-review__wrote"]'
                )
              );

              for (const container of listContainers) {
                const modifyElement =
                  container.querySelector(
                    '.js_reviewWroteListModifyBtn, a[href*="/wroteReviews/"][href*="/modify"]'
                  );
                const deleteElement =
                  container.querySelector(
                    '.js_reviewWroteListDeleteBtn, [data-reviewid], [data-review-id]'
                  );
                const element = modifyElement || deleteElement || container;
                const href = element.href || element.getAttribute('href') || '';
                const reviewId = findReviewId(element, href);
                if (!reviewId || seen.has(reviewId)) continue;
                seen.add(reviewId);
                items.push(buildItem(container, element, href, reviewId));
              }

              if (items.length > 0) return items;

              const candidates = Array.from(
                document.querySelectorAll(
                  '.js_reviewWroteListModifyBtn, .js_reviewWroteListDeleteBtn, a, button, [role="button"], [onclick], [data-reviewid], [data-review-id], [data-product-review-id], [data-review-no], [data-review-seq]'
                )
              ).filter((element) => {
                const href = element.href || element.getAttribute('href') || '';
                const label = normalizeText(element.textContent || element.getAttribute('aria-label') || '');
                return (
                  href.includes('/productreview/wroteReviews/') ||
                  href.includes('/modify') ||
                  label.includes('수정') ||
                  label.includes('삭제') ||
                  element.classList.contains('js_reviewWroteListModifyBtn') ||
                  element.classList.contains('js_reviewWroteListDeleteBtn') ||
                  element.hasAttribute('data-reviewid') ||
                  element.hasAttribute('data-review-id') ||
                  element.hasAttribute('data-product-review-id') ||
                  element.hasAttribute('data-review-no') ||
                  element.hasAttribute('data-review-seq')
                );
              });
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
                items.push(buildItem(container, element, href, reviewId));
              }

              return items;
            })()
            """,
        )
        if not isinstance(result, list):
            return None

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

    async def list_editable(self) -> ListEditableReviewsResult:
        """저장된 세션으로 쿠팡 작성 리뷰 목록을 조회합니다."""
        if not self.store.has_session():
            return self._to_editable_list_result(
                _ListReviewableBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN)
            )
        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_editable_review_items(self._browser_session)
            if browser_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    COUPANG_WROTE_REVIEWS_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    browser_result = await self._list_editable_review_items(self._browser_session)
                else:
                    browser_result = _ListReviewableBrowserResult(state=login_state)
            return self._to_editable_list_result(browser_result)
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._to_editable_list_result(
                _ListReviewableBrowserResult(state=CoupangReviewState.BROWSER_CLOSED)
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
                self._to_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN),
                )
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._upload_review_browser(
                self._browser_session,
                review_url=request.review_url,
                order_id=request.order_id,
                product_id=request.product_id,
                rating=request.rating,
                text=request.text,
            )
            if browser_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    request.review_url or COUPANG_REVIEW_REGISTER_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    browser_result = await self._upload_review_browser(
                        self._browser_session,
                        review_url=request.review_url,
                        order_id=request.order_id,
                        product_id=request.product_id,
                        rating=request.rating,
                        text=request.text,
                    )
                else:
                    browser_result = _ReviewUploadBrowserResult(state=login_state)
            return self._emit_upload_result(self._to_result(request, browser_result))
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._emit_upload_result(
                self._to_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED),
                )
            )
        finally:
            await self._close_browser_session()

    async def edit_review(self, request: ReviewEditRequest) -> ReviewEditResult:
        """작성된 리뷰를 수정합니다."""
        validation_error = self._validate_edit_request(request)
        if validation_error is not None:
            return self._emit_edit_result(
                self._failure_edit_result(request, validation_error)
            )

        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 수정을 시작합니다...")

        if not self.store.has_session():
            return self._emit_edit_result(
                self._to_edit_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN),
                )
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._edit_review_browser(
                self._browser_session,
                order_id=request.order_id,
                product_id=request.product_id,
                review_id=request.review_id,
                rating=request.rating,
                text=request.text,
            )
            if browser_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    build_review_modify_url(review_id=request.review_id),
                )
                if login_state == CoupangReviewState.SUCCESS:
                    browser_result = await self._edit_review_browser(
                        self._browser_session,
                        order_id=request.order_id,
                        product_id=request.product_id,
                        review_id=request.review_id,
                        rating=request.rating,
                        text=request.text,
                    )
                else:
                    browser_result = _ReviewUploadBrowserResult(state=login_state)
            return self._emit_edit_result(self._to_edit_result(request, browser_result))
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._emit_edit_result(
                self._to_edit_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED),
                )
            )
        finally:
            await self._close_browser_session()

    async def delete_review(self, request: ReviewDeleteRequest) -> ReviewDeleteResult:
        """작성된 리뷰를 삭제합니다."""
        validation_error = self._validate_delete_request(request)
        if validation_error is not None:
            return self._emit_delete_result(
                self._failure_delete_result(request, validation_error)
            )

        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 삭제를 시작합니다...")

        if not self.store.has_session():
            return self._emit_delete_result(
                self._to_delete_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.NOT_LOGGED_IN),
                )
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._delete_review_browser(
                self._browser_session,
                review_id=request.review_id,
            )
            if browser_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    COUPANG_WROTE_REVIEWS_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    browser_result = await self._delete_review_browser(
                        self._browser_session,
                        review_id=request.review_id,
                    )
                else:
                    browser_result = _ReviewUploadBrowserResult(state=login_state)
            return self._emit_delete_result(self._to_delete_result(request, browser_result))
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._emit_delete_result(
                self._to_delete_result(
                    request,
                    _ReviewUploadBrowserResult(state=CoupangReviewState.BROWSER_CLOSED),
                )
            )
        finally:
            await self._close_browser_session()

    def _to_list_result(
        self,
        browser_result: _ListReviewableBrowserResult,
    ) -> ListReviewableResult:
        if browser_result.state != CoupangReviewState.SUCCESS:
            message = browser_result.message or review_state_message(
                browser_result.state,
                fallback="리뷰 작성 가능 목록 조회에 실패했습니다.",
            )
            metadata = review_metadata(browser_result.state)
            return ListReviewableResult(
                provider=self.provider,
                success=False,
                message=message,
                items=(),
                error_code=metadata.error_code,
                retryable=metadata.retryable,
                next_tools=metadata.next_tools,
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
            provider=self.provider,
            success=True,
            message=format_reviewable_list(items),
            items=items,
        )

    def _to_editable_list_result(
        self,
        browser_result: _ListReviewableBrowserResult,
    ) -> ListEditableReviewsResult:
        if browser_result.state != CoupangReviewState.SUCCESS:
            message = browser_result.message or review_state_message(
                browser_result.state,
                fallback="리뷰 수정 가능 목록 조회에 실패했습니다.",
            )
            metadata = review_metadata(browser_result.state)
            return ListEditableReviewsResult(
                provider=self.provider,
                success=False,
                message=message,
                items=(),
                error_code=metadata.error_code,
                retryable=metadata.retryable,
                next_tools=metadata.next_tools,
            )

        items = tuple(
            EditableReviewItem(
                index=index,
                review_id=item.review_id,
                product_id=item.product_id,
                order_id=item.order_id,
                product_name=item.product_name,
                rating=item.rating,
                review_text=item.review_text,
                modify_url=item.modify_url,
            )
            for index, item in enumerate(browser_result.items, start=1)
            if isinstance(item, _EditableReviewItemData)
        )
        return ListEditableReviewsResult(
            provider=self.provider,
            success=True,
            message=format_editable_review_list(items),
            items=items,
        )

    def _to_result(
        self,
        request: ReviewUploadRequest,
        browser_result: _ReviewUploadBrowserResult,
    ) -> ReviewUploadResult:
        if browser_result.state == CoupangReviewState.SUCCESS:
            return ReviewUploadResult(
                provider=self.provider,
                success=True,
                message="쿠팡 리뷰 업로드 성공",
                order_id=request.order_id,
                product_id=request.product_id,
            )

        message = browser_result.message or review_state_message(
            browser_result.state,
            fallback="리뷰 업로드에 실패했습니다.",
        )
        metadata = review_metadata(browser_result.state)
        return ReviewUploadResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _failure_result(
        self,
        request: ReviewUploadRequest,
        message: str,
    ) -> ReviewUploadResult:
        metadata = review_metadata(CoupangReviewState.VALIDATION_ERROR)
        return ReviewUploadResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _to_edit_result(
        self,
        request: ReviewEditRequest,
        browser_result: _ReviewUploadBrowserResult,
    ) -> ReviewEditResult:
        if browser_result.state == CoupangReviewState.SUCCESS:
            return ReviewEditResult(
                provider=self.provider,
                success=True,
                message="쿠팡 리뷰 수정 성공",
                order_id=request.order_id,
                product_id=request.product_id,
                review_id=request.review_id,
            )

        message = browser_result.message or review_state_message(
            browser_result.state,
            fallback="리뷰 수정에 실패했습니다.",
        )
        metadata = review_metadata(browser_result.state)
        return ReviewEditResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            review_id=request.review_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _failure_edit_result(
        self,
        request: ReviewEditRequest,
        message: str,
    ) -> ReviewEditResult:
        metadata = review_metadata(CoupangReviewState.VALIDATION_ERROR)
        return ReviewEditResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            review_id=request.review_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _to_delete_result(
        self,
        request: ReviewDeleteRequest,
        browser_result: _ReviewUploadBrowserResult,
    ) -> ReviewDeleteResult:
        if browser_result.state == CoupangReviewState.SUCCESS:
            return ReviewDeleteResult(
                provider=self.provider,
                success=True,
                message="쿠팡 리뷰 삭제 성공",
                review_id=request.review_id,
                product_id=request.product_id,
                order_id=request.order_id,
            )

        message = browser_result.message or review_state_message(
            browser_result.state,
            fallback="리뷰 삭제에 실패했습니다.",
        )
        metadata = review_metadata(browser_result.state)
        return ReviewDeleteResult(
            provider=self.provider,
            success=False,
            message=message,
            review_id=request.review_id,
            product_id=request.product_id,
            order_id=request.order_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _failure_delete_result(
        self,
        request: ReviewDeleteRequest,
        message: str,
    ) -> ReviewDeleteResult:
        metadata = review_metadata(CoupangReviewState.VALIDATION_ERROR)
        return ReviewDeleteResult(
            provider=self.provider,
            success=False,
            message=message,
            review_id=request.review_id,
            product_id=request.product_id,
            order_id=request.order_id,
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    def _emit_upload_result(self, result: ReviewUploadResult) -> ReviewUploadResult:
        terminal = self.terminal
        if terminal is not None:
            if result.success:
                terminal.success(result.message)
        if not result.success and terminal is not None:
            terminal.error(result.message)
        return result

    def _emit_edit_result(self, result: ReviewEditResult) -> ReviewEditResult:
        terminal = self.terminal
        if terminal is not None:
            if result.success:
                terminal.success(result.message)
        if not result.success and terminal is not None:
            terminal.error(result.message)
        return result

    def _emit_delete_result(self, result: ReviewDeleteResult) -> ReviewDeleteResult:
        terminal = self.terminal
        if terminal is not None:
            if result.success:
                terminal.success(result.message)
        if not result.success and terminal is not None:
            terminal.error(result.message)
        return result

    def _validate_edit_request(self, request: ReviewEditRequest) -> str | None:
        if not request.review_id.strip():
            return "리뷰 ID는 비어 있을 수 없습니다."
        if not 1 <= request.rating <= 5:
            return "별점은 1점부터 5점 사이여야 합니다."
        return None

    def _validate_delete_request(self, request: ReviewDeleteRequest) -> str | None:
        if not request.review_id.strip():
            return "리뷰 ID는 비어 있을 수 없습니다."
        return None
