"""쿠팡 리뷰 조회/업로드/수정 서비스 진입점입니다."""

from __future__ import annotations

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import (
    EditableReviewItem,
    ListEditableReviewsResult,
    ListReviewableResult,
    ReviewEditRequest,
    ReviewEditResult,
    ReviewUploadRequest,
    ReviewUploadResult,
    ReviewableItem,
)

from .browser import deserialize_evaluate_result
from .edit import CoupangReviewEdit
from .state import CoupangReviewState, REVIEW_STATE_MESSAGES, review_state_message
from .type import (
    _EditableReviewItemData,
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
    _ReviewableItemData,
)
from .upload import CoupangReviewUpload
from .utils import format_editable_review_list, format_reviewable_list


class CoupangReviewService(CoupangReviewUpload, CoupangReviewEdit):
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

    async def list_editable(
        self,
        *,
        print_result: bool = True,
    ) -> ListEditableReviewsResult:
        """저장된 세션으로 쿠팡 작성 리뷰 목록을 조회합니다."""
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 리뷰 수정 가능 목록을 조회합니다...")

        if not self.store.has_session():
            return self._emit_editable_list_result(
                ListEditableReviewsResult(
                    provider=self.provider_name,
                    success=False,
                    message=REVIEW_STATE_MESSAGES[CoupangReviewState.NOT_LOGGED_IN],
                    items=(),
                ),
                print_result=print_result,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_editable_review_items(self._browser_session)
            return self._emit_editable_list_result(
                self._to_editable_list_result(browser_result),
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
                order_id=request.order_id,
                product_id=request.product_id,
                rating=request.rating,
                text=request.text,
            )
            return self._emit_upload_result(self._to_result(request, browser_result))
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
                self._failure_edit_result(
                    request,
                    REVIEW_STATE_MESSAGES[CoupangReviewState.NOT_LOGGED_IN],
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
            return self._emit_edit_result(self._to_edit_result(request, browser_result))
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
                provider=self.provider_name,
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
            provider=self.provider_name,
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
        return ReviewUploadResult(
            provider=self.provider_name,
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
                provider=self.provider_name,
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
            provider=self.provider_name,
            success=False,
            message=message,
            order_id=request.order_id,
            product_id=request.product_id,
            review_id=request.review_id,
        )

    def _emit_list_result(
        self,
        result: ListReviewableResult,
        *,
        print_result: bool = True,
    ) -> ListReviewableResult:
        terminal = self.terminal
        if print_result and terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    def _emit_upload_result(self, result: ReviewUploadResult) -> ReviewUploadResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    def _emit_editable_list_result(
        self,
        result: ListEditableReviewsResult,
        *,
        print_result: bool = True,
    ) -> ListEditableReviewsResult:
        terminal = self.terminal
        if print_result and terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    def _emit_edit_result(self, result: ReviewEditResult) -> ReviewEditResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    def _validate_edit_request(self, request: ReviewEditRequest) -> str | None:
        if not request.review_id.strip():
            return "리뷰 ID는 비어 있을 수 없습니다."
        if not 1 <= request.rating <= 5:
            return "별점은 1점부터 5점 사이여야 합니다."
        if not request.text.strip():
            return "리뷰 본문은 비어 있을 수 없습니다."
        return None
