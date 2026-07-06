from __future__ import annotations

from typing import Final

import anyio

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab
from k_commerce_cli.services.providers.coupang.product.parsing import (
    ProductBrowserResult,
    ProductIdentifiers,
    build_product_browser_result,
    parse_coupang_product_url,
)
from k_commerce_cli.services.providers.coupang.product.ocr import extract_product_image_text
from k_commerce_cli.services.providers.coupang.product.script import PRODUCT_BODY_LOAD_SCRIPT, PRODUCT_DETAIL_SCRIPT
from k_commerce_cli.services.providers.coupang.result_metadata import (
    BROWSER_CLOSED_EXCEPTIONS,
    BROWSER_CLOSED_METADATA,
    LOGIN_REQUIRED_METADATA,
    ResultMetadata,
    is_browser_closed_error,
)
from k_commerce_cli.services.providers.coupang.search.service import deserialize_evaluate_result
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import (
    ProductDetailRequest,
    ProductDetailResult,
    ProductOcrResult,
    ProviderName,
)

COUPANG_HOME_URL: Final = "https://www.coupang.com/"
PRODUCT_PAGE_READY_TIMEOUT_SECONDS: Final = 10.0
PRODUCT_PAGE_READY_POLL_SECONDS: Final = 0.8

PRODUCT_DETAIL_METADATA: Final[dict[str, ResultMetadata]] = {
    "invalid_url": ResultMetadata(error_code="invalid_url"),
    "not_logged_in": LOGIN_REQUIRED_METADATA,
    "browser_closed": BROWSER_CLOSED_METADATA,
    "page_load_failed": ResultMetadata(error_code="page_load_failed", retryable=True),
    "product_not_found": ResultMetadata(error_code="product_not_found"),
    "access_blocked": ResultMetadata(error_code="access_blocked", retryable=True),
}


class CoupangProductService:
    def __init__(
        self,
        provider: ProviderName,
        store: ProviderStore,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider = provider
        self.store = store
        self.browser = browser
        self.terminal = terminal
        self._browser_session: BrowserSession | None = None

    async def get_product_detail(self, request: ProductDetailRequest) -> ProductDetailResult:
        identifiers = parse_coupang_product_url(request.url)
        if identifiers is None:
            return self._failure_result(request.url, "invalid_url", "쿠팡 상품 URL이 아닙니다.")
        if not self.store.has_session():
            return self._failure_result(request.url, "not_logged_in", "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.")

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._collect_product_detail(request.url, identifiers)
            result = self._to_result(request, browser_result)
            if result.success:
                return await self._with_ocr(result)
            return result
        except BROWSER_CLOSED_EXCEPTIONS as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._failure_result(request.url, "browser_closed", "브라우저가 닫혀 상품 상세 수집을 완료하지 못했습니다.")
        finally:
            await self._close_browser_session()

    async def _collect_product_detail(
        self,
        url: str,
        identifiers: ProductIdentifiers,
    ) -> ProductBrowserResult:
        tab = self._active_tab(self._browser_session)
        await tab.get(COUPANG_HOME_URL)
        await anyio.sleep(1.0)
        await tab.get(url)
        return await self._wait_for_product_detail(tab, identifiers, url)

    async def _wait_for_product_detail(
        self,
        tab: BrowserTab,
        identifiers: ProductIdentifiers,
        url: str,
    ) -> ProductBrowserResult:
        deadline = anyio.current_time() + PRODUCT_PAGE_READY_TIMEOUT_SECONDS
        last_result = ProductBrowserResult(state="page_load_failed", message="상품 페이지 데이터를 읽지 못했습니다.")
        while True:
            raw = await self._evaluate_json(tab, PRODUCT_DETAIL_SCRIPT)
            if not isinstance(raw, dict):
                if anyio.current_time() >= deadline:
                    return last_result
                await anyio.sleep(PRODUCT_PAGE_READY_POLL_SECONDS)
                continue

            result = build_product_browser_result(raw, identifiers, url)
            if self._is_product_page_ready(raw, result):
                return result
            last_result = result
            if anyio.current_time() >= deadline:
                return last_result
            if result.state == "success":
                await self._load_product_body(tab)
            await anyio.sleep(PRODUCT_PAGE_READY_POLL_SECONDS)

    async def _load_product_body(self, tab: BrowserTab) -> None:
        await self._evaluate_json(tab, PRODUCT_BODY_LOAD_SCRIPT)

    def _is_product_page_ready(self, raw: dict, result: ProductBrowserResult) -> bool:
        if result.state == "success":
            return bool(result.required_info or result.detail_images or result.sections or result.tables)
        return result.state != "product_not_found" or str(raw.get("state") or "success") != "success"

    def _to_result(self, request: ProductDetailRequest, browser_result: ProductBrowserResult) -> ProductDetailResult:
        if browser_result.state != "success":
            return self._failure_result(
                request.url,
                browser_result.state,
                browser_result.message or "상품 상세 수집에 실패했습니다.",
            )

        return ProductDetailResult(
            success=True,
            provider=self.provider.value,
            message=browser_result.message,
            url=request.url,
            product=browser_result.product,
            required_info=browser_result.required_info,
            detail_images=browser_result.detail_images,
            sections=browser_result.sections,
            tables=browser_result.tables,
        )

    async def _with_ocr(self, result: ProductDetailResult) -> ProductDetailResult:
        detail_images, ocr = await extract_product_image_text(result.detail_images)
        return ProductDetailResult(
            success=result.success,
            provider=result.provider,
            message=result.message,
            url=result.url,
            product=result.product,
            required_info=result.required_info,
            detail_images=detail_images,
            sections=result.sections,
            tables=result.tables,
            ocr=ocr,
            error_code=result.error_code,
            retryable=result.retryable,
            next_tools=result.next_tools,
        )

    def _failure_result(self, url: str, state: str, message: str) -> ProductDetailResult:
        metadata = PRODUCT_DETAIL_METADATA.get(state, ResultMetadata(error_code=state, retryable=True))
        return ProductDetailResult(
            success=False,
            provider=self.provider.value,
            message=message,
            url=url,
            product=None,
            required_info=(),
            detail_images=(),
            sections=(),
            tables=(),
            ocr=ProductOcrResult(enabled=False, status="skipped", model="", scope="summary"),
            error_code=metadata.error_code,
            retryable=metadata.retryable,
            next_tools=metadata.next_tools,
        )

    async def _evaluate_json(self, tab: BrowserTab, script: str):
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return None
        result = await evaluate(script)
        if getattr(result, "__class__", None) and result.__class__.__name__ == "ExceptionDetails":
            return None
        return deserialize_evaluate_result(result)

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return
        try:
            await self.browser.close(self._browser_session)
        except BROWSER_CLOSED_EXCEPTIONS as exc:
            if not is_browser_closed_error(exc):
                raise
        finally:
            self._browser_session = None

    def _active_tab(self, session: BrowserSession | None) -> BrowserTab:
        if session is None:
            msg = "Browser session is not open"
            raise RuntimeError(msg)
        return session.tab
