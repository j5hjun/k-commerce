from dataclasses import asdict
from urllib.parse import quote

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab, Store
from k_commerce_cli.services.types import (
    EditableReviewItem,
    ListEditableReviewsResult,
    ListReviewsResult,
    ListReviewableResult,
    ProviderName,
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
from .state import CoupangReviewState, REVIEW_STATE_MESSAGES, review_state_message
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

    async def list_reviewable(self, refresh: bool = False) -> ListReviewableResult:
        """저장된 세션으로 쿠팡 리뷰 작성 가능 상품 목록을 조회합니다."""
        if not refresh:
            cached = self._load_cached_reviews()
            if cached is not None:
                return cached.reviewable

        result = await self.list_reviews(refresh=True)
        return result.reviewable

    async def list_reviews(self, refresh: bool = False) -> ListReviewsResult:
        """한 브라우저 세션으로 작성 가능 리뷰와 작성한 리뷰 목록을 순차 조회합니다."""
        if not refresh:
            cached = self._load_cached_reviews()
            if cached is not None:
                if self.terminal is not None:
                    self.terminal.cache("저장된 리뷰 목록을 바로 불러옵니다.")
                return cached

        result = await self._collect_reviews_from_browser()
        if result.success:
            self._write_cached_reviews(result)
        return result

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

    async def list_editable(self, refresh: bool = False) -> ListEditableReviewsResult:
        """저장된 세션으로 쿠팡 작성 리뷰 목록을 조회합니다."""
        if not refresh:
            cached = self._load_cached_reviews()
            if cached is not None:
                return cached.editable

        result = await self.list_reviews(refresh=True)
        return result.editable

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        """선택한 주문 상품에 별점과 리뷰 본문을 업로드합니다."""
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 업로드를 시작합니다...")

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
            result = self._emit_upload_result(self._to_result(request, browser_result))
            if result.success:
                await self._refresh_reviews_cache()
            return result
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
            result = self._emit_edit_result(self._to_edit_result(request, browser_result))
            if result.success:
                await self._refresh_reviews_cache()
            return result
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
            result = self._emit_delete_result(self._to_delete_result(request, browser_result))
            if result.success:
                await self._refresh_reviews_cache()
            return result
        finally:
            await self._close_browser_session()

    async def _collect_reviews_from_browser(self) -> ListReviewsResult:
        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            reviewable_result = await self._list_reviewable_items(self._browser_session)
            if reviewable_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    COUPANG_REVIEWABLE_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    reviewable_result = await self._list_reviewable_items(self._browser_session)
                else:
                    reviewable_result = _ListReviewableBrowserResult(state=login_state)

            editable_result = await self._list_editable_review_items(self._browser_session)
            if editable_result.state == CoupangReviewState.NOT_LOGGED_IN:
                login_state = await self._open_login_and_wait_for_review(
                    self._browser_session,
                    COUPANG_WROTE_REVIEWS_URL,
                )
                if login_state == CoupangReviewState.SUCCESS:
                    editable_result = await self._list_editable_review_items(self._browser_session)
                else:
                    editable_result = _ListReviewableBrowserResult(state=login_state)

            reviewable = self._to_list_result(reviewable_result)
            editable = self._to_editable_list_result(editable_result)
            success = reviewable.success and editable.success
            message = (
                "리뷰 목록을 불러왔습니다."
                if success
                else reviewable.message or editable.message or "리뷰 목록을 불러오지 못했습니다."
            )
            return ListReviewsResult(
                provider=self.provider,
                success=success,
                message=message,
                reviewable=reviewable,
                editable=editable,
            )
        finally:
            await self._close_browser_session()

    async def _refresh_reviews_cache(self) -> None:
        result = await self._collect_reviews_from_browser()
        if result.success:
            self._write_cached_reviews(result)

    def _load_cached_reviews(self) -> ListReviewsResult | None:
        payload = self.store.load_reviews()
        if payload is None:
            return None
        try:
            reviewable_payload = payload.get("reviewable")
            editable_payload = payload.get("editable")
            if not isinstance(reviewable_payload, dict) or not isinstance(editable_payload, dict):
                return None

            reviewable_items = tuple(
                ReviewableItem(
                    index=int(item.get("index") or 0),
                    product_id=str(item.get("product_id") or ""),
                    product_name=str(item.get("product_name") or ""),
                    delivery_date=str(item.get("delivery_date") or ""),
                    completed_order_vendor_item_id=str(
                        item.get("completed_order_vendor_item_id") or ""
                    ),
                    vendor_item_id=str(item.get("vendor_item_id") or ""),
                    review_url=str(item.get("review_url") or ""),
                )
                for item in reviewable_payload.get("items", [])
                if isinstance(item, dict)
            )
            editable_items = tuple(
                EditableReviewItem(
                    index=int(item.get("index") or 0),
                    review_id=str(item.get("review_id") or ""),
                    product_id=str(item.get("product_id") or ""),
                    order_id=str(item.get("order_id") or ""),
                    product_name=str(item.get("product_name") or ""),
                    rating=int(item.get("rating") or 0),
                    review_text=str(item.get("review_text") or ""),
                    modify_url=str(item.get("modify_url") or ""),
                )
                for item in editable_payload.get("items", [])
                if isinstance(item, dict)
            )
            reviewable = ListReviewableResult(
                provider=ProviderName(str(reviewable_payload.get("provider") or self.provider)),
                success=bool(reviewable_payload.get("success", True)),
                message=str(reviewable_payload.get("message") or format_reviewable_list(reviewable_items)),
                items=reviewable_items,
            )
            editable = ListEditableReviewsResult(
                provider=ProviderName(str(editable_payload.get("provider") or self.provider)),
                success=bool(editable_payload.get("success", True)),
                message=str(
                    editable_payload.get("message") or format_editable_review_list(editable_items)
                ),
                items=editable_items,
            )
            return ListReviewsResult(
                provider=ProviderName(str(payload.get("provider") or self.provider)),
                success=bool(payload.get("success", reviewable.success and editable.success)),
                message=str(payload.get("message") or "리뷰 목록을 불러왔습니다."),
                reviewable=reviewable,
                editable=editable,
            )
        except (TypeError, ValueError):
            return None

    def _write_cached_reviews(self, result: ListReviewsResult) -> None:
        self.store.write_reviews(
            {
                "provider": str(result.provider),
                "success": result.success,
                "message": result.message,
                "reviewable": {
                    "provider": str(result.reviewable.provider),
                    "success": result.reviewable.success,
                    "message": result.reviewable.message,
                    "items": [asdict(item) for item in result.reviewable.items],
                },
                "editable": {
                    "provider": str(result.editable.provider),
                    "success": result.editable.success,
                    "message": result.editable.message,
                    "items": [asdict(item) for item in result.editable.items],
                },
            }
        )

    def _to_list_result(
        self,
        browser_result: _ListReviewableBrowserResult,
    ) -> ListReviewableResult:
        if browser_result.state != CoupangReviewState.SUCCESS:
            message = browser_result.message or review_state_message(
                browser_result.state,
                fallback="리뷰 작성 가능 목록 조회에 실패했습니다.",
            )
            return ListReviewableResult(
                provider=self.provider,
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
            return ListEditableReviewsResult(
                provider=self.provider,
                success=False,
                message=message,
                items=(),
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
        return self._failure_result(request, message)

    def _failure_result(
        self,
        request: ReviewUploadRequest,
        message: str,
    ) -> ReviewUploadResult:
        return ReviewUploadResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
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
        return self._failure_edit_result(request, message)

    def _failure_edit_result(
        self,
        request: ReviewEditRequest,
        message: str,
    ) -> ReviewEditResult:
        return ReviewEditResult(
            provider=self.provider,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            review_id=request.review_id,
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
        return self._failure_delete_result(request, message)

    def _failure_delete_result(
        self,
        request: ReviewDeleteRequest,
        message: str,
    ) -> ReviewDeleteResult:
        return ReviewDeleteResult(
            provider=self.provider,
            success=False,
            message=message,
            review_id=request.review_id,
            product_id=request.product_id,
            order_id=request.order_id,
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
