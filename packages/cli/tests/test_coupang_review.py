from __future__ import annotations

from pathlib import Path
from itertools import repeat
from unittest.mock import AsyncMock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.providers.coupang.review.service import (
    CoupangReviewService,
    _EditableReviewItemData,
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
    _ReviewableItemData,
    deserialize_evaluate_result,
)
from k_commerce_cli.services.providers.coupang.review.state import CoupangReviewState
from k_commerce_cli.services.providers.coupang.review.utils import (
    build_review_modify_url,
    build_review_register_url,
    format_deletable_review_list,
    format_reviewable_list,
)
from k_commerce_cli.services.registry import get_provider, list_providers
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import (
    EditableReviewItem,
    ProviderName,
    ReviewDeleteRequest,
    ReviewEditRequest,
    ReviewUploadRequest,
    ReviewableItem,
)

SAMPLE_REVIEW_URL = (
    "https://my.coupang.com/productreview/register?"
    "completedOrderVendorItemId=22404668406&"
    "productId=8825977723&"
    "deliveryDate=2026-06-15&"
    "vendorItemId=92707464866"
)


def test_get_provider_returns_coupang_provider_instance() -> None:
    provider = get_provider("coupang")

    assert isinstance(provider, CoupangProvider)


def test_get_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported provider: unknown. Supported providers: coupang",
    ):
        get_provider("unknown")


def test_list_providers_includes_builtin_coupang_provider() -> None:
    assert list_providers() == ["coupang"]


class _BrowserSpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.save_session = AsyncMock()
        self.close = AsyncMock()
        self.select = AsyncMock(return_value=None)


class _EvaluateTab:
    def __init__(self, payloads: list[object]) -> None:
        self._payloads = list(payloads)
        self.evaluate_calls: list[str] = []

    async def evaluate(self, _script: str, _args=None):
        self.evaluate_calls.append(_script)
        if not self._payloads:
            return []
        return self._payloads.pop(0)


class _ClosingTab:
    async def get(self, _url: str) -> None:
        raise RuntimeError("browser closed")


class _Session:
    def __init__(self, tab: object) -> None:
        self.tab = tab


def _make_review_service(
    *,
    root_dir: Path | None = None,
    browser: _BrowserSpy | None = None,
) -> CoupangReviewService:
    resolved_root = root_dir if root_dir is not None else Path.home() / ".k-commerce"
    return CoupangReviewService(
        provider=ProviderName.COUPANG,
        store=ProviderStore(ProviderPaths("coupang", root_dir=resolved_root)),
        browser=browser or _BrowserSpy(),
    )


def _request() -> ReviewUploadRequest:
    return ReviewUploadRequest(
        order_id="22404668406",
        product_id="8825977723",
        rating=5,
        text="좋아요",
        review_url=SAMPLE_REVIEW_URL,
    )


def _edit_request() -> ReviewEditRequest:
    return ReviewEditRequest(
        order_id="22404668406",
        product_id="8825977723",
        review_id="934113278",
        rating=4,
        text="수정된 리뷰",
    )


def _delete_request() -> ReviewDeleteRequest:
    return ReviewDeleteRequest(
        order_id="22404668406",
        product_id="8825977723",
        review_id="934113278",
    )


def test_build_review_register_url() -> None:
    assert build_review_register_url(
        completed_order_vendor_item_id="22404668406",
        product_id="8825977723",
        delivery_date="2026-06-15",
        vendor_item_id="92707464866",
    ) == SAMPLE_REVIEW_URL


def test_build_review_modify_url() -> None:
    assert build_review_modify_url(review_id="934113278") == (
        "https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1"
    )


def test_format_reviewable_list_returns_empty_message() -> None:
    assert format_reviewable_list(()) == "리뷰 작성 가능한 상품이 없습니다."


def test_format_reviewable_list_formats_table() -> None:
    items = (
        ReviewableItem(
            index=1,
            product_id="8825977723",
            product_name="포스트 아몬드후레이크 620g, 620g, 1개",
            delivery_date="2026-03-29",
            completed_order_vendor_item_id="22404668406",
            vendor_item_id="92707464866",
            review_url="https://my.coupang.com/productreview/register?completedOrderVendorItemId=22404668406",
        ),
    )

    output = format_reviewable_list(items)

    assert "리뷰 작성 가능 (1건):" in output
    assert "8825977723" in output
    assert "2026-03-29" in output
    assert "포스트 아몬드후레이크" in output


def test_format_reviewable_list_truncates_long_product_name() -> None:
    items = (
        ReviewableItem(
            index=1,
            product_id="8825977723",
            product_name="가" * 60,
            delivery_date="2026-03-29",
            completed_order_vendor_item_id="22404668406",
            vendor_item_id="92707464866",
            review_url="https://example.com",
        ),
    )

    output = format_reviewable_list(items)

    assert "..." in output
    assert "가" * 60 not in output


def test_format_deletable_review_list_uses_delete_label() -> None:
    items = (
        EditableReviewItem(
            index=2,
            review_id="934113278",
            product_id="8825977723",
            order_id="22404668406",
            product_name="포스트 아몬드후레이크",
            rating=5,
            review_text="예전 리뷰",
            modify_url="https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1",
        ),
    )

    output = format_deletable_review_list(items)

    assert "리뷰 삭제 가능 (1건):" in output
    assert "  2  " in output
    assert "No" in output
    assert "리뷰ID" not in output
    assert "934113278" not in output


def test_deserialize_evaluate_result_converts_cdp_object() -> None:
    value = {
        "type": "object",
        "value": [
            ["product_id", {"type": "string", "value": "8825977723"}],
            ["completed_order_vendor_item_id", {"type": "string", "value": "22404668406"}],
        ],
    }

    assert deserialize_evaluate_result(value) == {
        "product_id": "8825977723",
        "completed_order_vendor_item_id": "22404668406",
    }


@pytest.mark.anyio
async def test_active_tab_falls_back_when_browser_has_no_page_targets() -> None:
    class _RuntimeWithoutPages:
        tabs: list[object] = []

        @property
        def main_tab(self) -> object:
            raise StopIteration

    service = _make_review_service()
    tab = _EvaluateTab([])
    session = _Session(tab)
    session.browser = _RuntimeWithoutPages()  # type: ignore[attr-defined]

    assert service._active_tab(session) is tab


@pytest.mark.anyio
async def test_is_review_login_screen_uses_dom_not_tab_url_attribute() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])

    assert await service._is_review_login_screen(tab) is True
    assert "login.coupang.com" in tab.evaluate_calls[0]
    assert "로그인이 필요" in tab.evaluate_calls[0]


@pytest.mark.anyio
async def test_open_login_and_wait_skips_login_navigation_when_already_on_login_screen() -> None:
    class _LoginScreenTab:
        url = "https://my.coupang.com/productreview/reviewable"

        def __init__(self) -> None:
            self.get_calls: list[str] = []

        async def get(self, url: str) -> None:
            self.get_calls.append(url)

        async def evaluate(self, script: str):
            if "passwordInput" in script:
                return True
            if "window.location.href" in script and "body_text" in script:
                return {
                    "url": "https://login.coupang.com/login/login.pang",
                    "body_text": "로그인",
                }
            if "login.coupang.com" in script and "has_login_link" in script:
                return {
                    "url": "https://login.coupang.com/login/login.pang",
                    "has_login_link": False,
                    "has_mycoupang_link": False,
                }
            return False

    service = _make_review_service()
    tab = _LoginScreenTab()
    session = _Session(tab)

    state = await service._open_login_and_wait_for_review(
        session,
        "https://my.coupang.com/productreview/reviewable",
        poll_count=1,
    )

    assert tab.get_calls == []
    assert state == CoupangReviewState.NOT_LOGGED_IN


@pytest.mark.anyio
async def test_read_review_register_state_deserializes_cdp_success_result() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            {
                "type": "object",
                "value": [
                    ["state", {"type": "string", "value": "success"}],
                    ["message", {"type": "string", "value": ""}],
                ],
            }
        ]
    )

    page_state = await service._read_review_register_state(tab, "8825977723", "22404668406")

    assert page_state == "success"


@pytest.mark.anyio
async def test_read_review_register_state_checks_url_query_before_form_success() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([{"state": "success"}])

    page_state = await service._read_review_register_state(tab, "8825977723", "22404668406")

    assert page_state == "success"
    script = tab.evaluate_calls[0]
    assert "params.get('productId')" in script
    assert "params.get('completedOrderVendorItemId')" in script
    assert script.index("pageProductId && pageProductId !== productId") < script.index(
        "const reviewForm = document.querySelector"
    )
    assert script.index("pageOrderId && pageOrderId !== orderId") < script.index(
        "const reviewForm = document.querySelector"
    )


@pytest.mark.anyio
async def test_scrape_reviewable_items_parses_data_reference_buttons() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            [
                {
                    "type": "object",
                    "value": [
                        ["product_id", {"type": "string", "value": "8825977723"}],
                        ["product_name", {"type": "string", "value": "포스트 아몬드후레이크"}],
                        ["delivery_date", {"type": "string", "value": "2026-03-29"}],
                        [
                            "completed_order_vendor_item_id",
                            {"type": "string", "value": "22404668406"},
                        ],
                        ["vendor_item_id", {"type": "string", "value": "92707464866"}],
                    ],
                }
            ]
        ]
    )

    items = await service._scrape_reviewable_items(tab)

    assert len(items) == 1
    assert items[0].product_id == "8825977723"
    assert items[0].completed_order_vendor_item_id == "22404668406"
    assert "productreview/register" in items[0].review_url


@pytest.mark.anyio
async def test_scrape_reviewable_items_skips_incomplete_entries() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            [
                {
                    "type": "object",
                    "value": [
                        ["product_id", {"type": "string", "value": ""}],
                        [
                            "completed_order_vendor_item_id",
                            {"type": "string", "value": "22404668406"},
                        ],
                        ["vendor_item_id", {"type": "string", "value": "92707464866"}],
                        ["delivery_date", {"type": "string", "value": "2026-03-29"}],
                    ],
                }
            ]
        ]
    )

    items = await service._scrape_reviewable_items(tab)

    assert items == ()


@pytest.mark.anyio
async def test_scrape_editable_review_items_parses_modify_links() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            [
                {
                    "type": "object",
                    "value": [
                        ["review_id", {"type": "string", "value": "934113278"}],
                        ["product_id", {"type": "string", "value": "8825977723"}],
                        ["order_id", {"type": "string", "value": "22404668406"}],
                        ["product_name", {"type": "string", "value": "포스트 아몬드후레이크"}],
                        ["rating", {"type": "number", "value": 5}],
                        ["review_text", {"type": "string", "value": "예전 리뷰"}],
                        [
                            "modify_url",
                            {
                                "type": "string",
                                "value": "https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1",
                            },
                        ],
                    ],
                }
            ]
        ]
    )

    items = await service._scrape_editable_review_items(tab)

    assert len(items) == 1
    assert items[0].review_id == "934113278"
    assert items[0].product_id == "8825977723"
    assert items[0].rating == 5
    script = tab.evaluate_calls[0]
    assert ".js_reviewWroteListModifyBtn" in script
    assert "js_reviewWroteListDeleteBtn" in script
    assert "li.my-review__wrote__list" in script
    assert ".wrote-list-rating-active" in script


@pytest.mark.anyio
async def test_scrape_editable_review_items_builds_modify_url_from_review_id() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            [
                {
                    "review_id": "934113278",
                    "product_id": "8723409516",
                    "order_id": "",
                    "product_name": "동원 어단백 닭가슴살 피쉬 프로틴바",
                    "rating": 0,
                    "review_text": "",
                    "modify_url": "",
                }
            ]
        ]
    )

    items = await service._scrape_editable_review_items(tab)

    assert len(items) == 1
    assert items[0].modify_url == (
        "https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1"
    )


@pytest.mark.anyio
async def test_is_page_scrolled_to_bottom_returns_true_when_evaluate_succeeds() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])

    assert await service._is_page_scrolled_to_bottom(tab) is True


@pytest.mark.anyio
async def test_list_editable_waits_for_bottom_before_stopping_scroll() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])
    session = _Session(tab)
    service._open_wrote_reviews = AsyncMock()
    service._is_logged_in = AsyncMock(return_value=True)
    service._read_review_page_state = AsyncMock(return_value={"read_failed": False})
    service._scroll_page = AsyncMock()
    service._is_page_scrolled_to_bottom = AsyncMock(side_effect=[False, False, True, True, True])
    two_items = (
        _EditableReviewItemData(
            review_id="1",
            product_id="p1",
            order_id="o1",
            product_name="상품1",
            rating=5,
            review_text="",
            modify_url="https://my.coupang.com/productreview/wroteReviews/1/modify?page=1",
        ),
        _EditableReviewItemData(
            review_id="2",
            product_id="p2",
            order_id="o2",
            product_name="상품2",
            rating=4,
            review_text="",
            modify_url="https://my.coupang.com/productreview/wroteReviews/2/modify?page=1",
        ),
    )
    one_item = (two_items[0],)
    service._scrape_editable_review_items = AsyncMock(
        side_effect=[one_item, one_item, two_items, *repeat(two_items, 10)]
    )

    result = await service._list_editable_review_items(session)

    assert result.state == CoupangReviewState.SUCCESS
    assert len(result.items) == 2
    assert service._scroll_page.await_count >= 3
    assert service._is_page_scrolled_to_bottom.await_count >= 3


@pytest.mark.anyio
async def test_submit_review_form_supports_coupang_modify_selectors() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])

    submitted = await service._submit_review_form(tab, 4, "맛있어요")

    assert submitted is True
    script = tab.evaluate_calls[0]
    assert ".js_reviewModifyStarBtn" in script
    assert ".js_reviewModifyTextArea" in script
    assert ".js_reviewModifySubmitBtn" in script
    assert "label.includes('완료')" in script
    assert ".js_reviewWritableStarBtn" in script


@pytest.mark.anyio
async def test_submit_review_form_allows_empty_review_text() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])

    submitted = await service._submit_review_form(tab, 3, "")

    assert submitted is True
    script = tab.evaluate_calls[0]
    assert "if (!textarea && text) return false;" in script
    assert "textarea.value = text;" in script


@pytest.mark.anyio
async def test_delete_review_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    session = object()
    browser.launch.return_value = session
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._delete_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)
    )
    service._refresh_reviews_cache = AsyncMock()

    result = await service.delete_review(_delete_request())

    assert result.success is True
    assert result.message == "쿠팡 리뷰 삭제 성공"
    assert result.review_id == "934113278"
    service._delete_review_browser.assert_awaited_once_with(
        session,
        review_id="934113278",
    )
    service._refresh_reviews_cache.assert_awaited_once()


@pytest.mark.anyio
async def test_read_review_delete_confirmation_accepts_success_modal() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([{"state": "success"}])

    confirmation = await service._read_review_delete_confirmation(tab, "934113278")

    assert confirmation == "success"
    script = tab.evaluate_calls[0]
    assert "구매후기가 삭제되었습니다" in script
    assert ".js_reviewWroteListDeleteBtn" in script


@pytest.mark.anyio
async def test_click_delete_review_button_finds_delete_via_modify_container() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])

    clicked = await service._click_delete_review_button(tab, "934113278")

    assert clicked is True
    script = tab.evaluate_calls[0]
    assert "js_reviewWroteListModifyBtn" in script
    assert "/wroteReviews/${reviewId}/" in script


@pytest.mark.anyio
async def test_delete_review_browser_scrolls_until_delete_button_found() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])
    session = _Session(tab)
    service._open_wrote_reviews = AsyncMock()
    service._is_logged_in = AsyncMock(return_value=True)
    service._read_review_page_state = AsyncMock(return_value={"read_failed": False})
    service._click_delete_review_button = AsyncMock(side_effect=[False, False, True])
    service._scroll_page = AsyncMock()
    service._confirm_delete_review = AsyncMock(return_value=True)
    service._read_review_delete_confirmation = AsyncMock(return_value=CoupangReviewState.SUCCESS)

    result = await service._delete_review_browser(session, review_id="934113278")

    assert result.state == CoupangReviewState.SUCCESS
    assert service._click_delete_review_button.await_count == 3
    assert service._scroll_page.await_count == 2


@pytest.mark.anyio
async def test_list_editable_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._list_editable_review_items = AsyncMock(
        return_value=_ListReviewableBrowserResult(
            state=CoupangReviewState.SUCCESS,
            items=(
                _EditableReviewItemData(
                    review_id="934113278",
                    product_id="8825977723",
                    order_id="22404668406",
                    product_name="포스트 아몬드후레이크",
                    rating=5,
                    review_text="예전 리뷰",
                    modify_url="https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1",
                ),
            ),
        )
    )

    result = await service.list_editable()

    assert result.success is True
    assert len(result.items) == 1
    assert result.items[0].review_id == "934113278"
    assert result.items[0].rating == 5
    assert "리뷰 수정 가능 (1건):" in result.message
    assert "★★★★★" in result.message
    assert "예전 리뷰" in result.message


@pytest.mark.anyio
async def test_list_reviewable_waits_for_bottom_before_stopping_scroll() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([True])
    session = _Session(tab)
    service._open_reviewable_list = AsyncMock()
    service._is_logged_in = AsyncMock(return_value=True)
    service._read_review_page_state = AsyncMock(
        return_value={"read_failed": False, "url": "https://my.coupang.com/productreview/reviewable"}
    )
    service._scroll_page = AsyncMock()
    service._is_page_scrolled_to_bottom = AsyncMock(side_effect=[False, False, True, True, True])
    two_items = (
        _ReviewableItemData(
            product_id="p1",
            product_name="상품1",
            delivery_date="2026-03-29",
            completed_order_vendor_item_id="o1",
            vendor_item_id="v1",
            review_url="https://my.coupang.com/productreview/register?productId=p1",
        ),
        _ReviewableItemData(
            product_id="p2",
            product_name="상품2",
            delivery_date="2026-03-30",
            completed_order_vendor_item_id="o2",
            vendor_item_id="v2",
            review_url="https://my.coupang.com/productreview/register?productId=p2",
        ),
    )
    one_item = (two_items[0],)
    service._scrape_reviewable_items = AsyncMock(
        side_effect=[one_item, one_item, two_items, *repeat(two_items, 10)]
    )

    result = await service._list_reviewable_items(session)

    assert result.state == CoupangReviewState.SUCCESS
    assert len(result.items) == 2
    assert service._scroll_page.await_count >= 3
    assert service._is_page_scrolled_to_bottom.await_count >= 3


@pytest.mark.anyio
async def test_list_reviewable_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._list_reviewable_items = AsyncMock(
        return_value=_ListReviewableBrowserResult(
            state=CoupangReviewState.SUCCESS,
            items=(
                _ReviewableItemData(
                    product_id="8825977723",
                    product_name="포스트 아몬드후레이크",
                    delivery_date="2026-03-29",
                    completed_order_vendor_item_id="22404668406",
                    vendor_item_id="92707464866",
                    review_url=(
                        "https://my.coupang.com/productreview/register?"
                        "completedOrderVendorItemId=22404668406&productId=8825977723"
                    ),
                ),
            ),
        )
    )

    result = await service.list_reviewable()

    assert result.success is True
    assert len(result.items) == 1
    assert result.items[0].index == 1
    assert result.items[0].product_id == "8825977723"
    assert "리뷰 작성 가능 (1건):" in result.message
    browser.launch.assert_awaited_once()
    service._list_reviewable_items.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_list_reviewable_returns_browser_closed_when_tab_is_closed() -> None:
    service = _make_review_service()

    result = await service._list_reviewable_items(_Session(_ClosingTab()))

    assert result.state == CoupangReviewState.BROWSER_CLOSED


@pytest.mark.anyio
async def test_list_reviewable_fails_when_session_is_missing(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service._list_reviewable_items = AsyncMock(
        return_value=_ListReviewableBrowserResult(
            state=CoupangReviewState.NOT_LOGGED_IN,
        )
    )
    service._open_login_and_wait_for_review = AsyncMock(
        return_value=CoupangReviewState.NOT_LOGGED_IN
    )

    result = await service.list_reviewable()

    assert result.success is False
    assert result.items == ()
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


@pytest.mark.anyio
async def test_list_reviewable_fails_when_not_logged_in(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._list_reviewable_items = AsyncMock(
        return_value=_ListReviewableBrowserResult(
            state=CoupangReviewState.NOT_LOGGED_IN,
            message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
        )
    )
    service._open_login_and_wait_for_review = AsyncMock(
        return_value=CoupangReviewState.NOT_LOGGED_IN
    )

    result = await service.list_reviewable()

    assert result.success is False
    assert result.items == ()
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


@pytest.mark.anyio
async def test_upload_review_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    session = object()
    browser.launch.return_value = session
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)
    )
    service._refresh_reviews_cache = AsyncMock()

    result = await service.upload_review(_request())

    assert result.success is True
    assert result.message == "쿠팡 리뷰 업로드 성공"
    assert result.order_id == "22404668406"
    assert result.product_id == "8825977723"
    browser.launch.assert_awaited_once()
    service._upload_review_browser.assert_awaited_once_with(
        session,
        review_url=_request().review_url,
        order_id="22404668406",
        product_id="8825977723",
        rating=5,
        text="좋아요",
    )
    service._refresh_reviews_cache.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_upload_review_fails_when_session_is_missing(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.NOT_LOGGED_IN,
        )
    )
    service._open_login_and_wait_for_review = AsyncMock(
        return_value=CoupangReviewState.NOT_LOGGED_IN
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


@pytest.mark.anyio
async def test_upload_review_fails_when_not_logged_in(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.NOT_LOGGED_IN,
            message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
        )
    )
    service._open_login_and_wait_for_review = AsyncMock(
        return_value=CoupangReviewState.NOT_LOGGED_IN
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


@pytest.mark.anyio
async def test_upload_review_fails_when_order_not_found(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.ORDER_NOT_FOUND,
            message="지정한 주문을 찾을 수 없습니다.",
        )
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "지정한 주문을 찾을 수 없습니다."


@pytest.mark.anyio
async def test_upload_review_fails_when_product_not_found(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.PRODUCT_NOT_FOUND,
            message="지정한 상품을 찾을 수 없습니다.",
        )
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "지정한 상품을 찾을 수 없습니다."


@pytest.mark.anyio
async def test_upload_review_fails_when_already_reviewed(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.ALREADY_REVIEWED,
            message="이미 리뷰가 작성된 상품입니다.",
        )
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "이미 리뷰가 작성된 상품입니다."


@pytest.mark.anyio
async def test_upload_review_fails_when_not_reviewable(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._upload_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.NOT_REVIEWABLE,
            message="리뷰를 작성할 수 없는 상품입니다.",
        )
    )

    result = await service.upload_review(_request())

    assert result.success is False
    assert result.message == "리뷰를 작성할 수 없는 상품입니다."


@pytest.mark.anyio
async def test_edit_review_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    session = object()
    browser.launch.return_value = session
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)
    )
    service._refresh_reviews_cache = AsyncMock()

    result = await service.edit_review(_edit_request())

    assert result.success is True
    assert result.message == "쿠팡 리뷰 수정 성공"
    assert result.review_id == "934113278"
    service._edit_review_browser.assert_awaited_once_with(
        session,
        order_id="22404668406",
        product_id="8825977723",
        review_id="934113278",
        rating=4,
        text="수정된 리뷰",
    )
    service._refresh_reviews_cache.assert_awaited_once()


@pytest.mark.anyio
async def test_edit_review_fails_when_session_is_missing(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.NOT_LOGGED_IN,
        )
    )
    service._open_login_and_wait_for_review = AsyncMock(
        return_value=CoupangReviewState.NOT_LOGGED_IN
    )

    result = await service.edit_review(_edit_request())

    assert result.success is False
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


@pytest.mark.anyio
async def test_edit_review_fails_when_review_not_found(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.REVIEW_NOT_FOUND,
            message="작성된 리뷰를 찾을 수 없습니다.",
        )
    )

    result = await service.edit_review(_edit_request())

    assert result.success is False
    assert result.message == "작성된 리뷰를 찾을 수 없습니다."


@pytest.mark.anyio
async def test_edit_review_fails_when_not_editable(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.NOT_EDITABLE,
            message="리뷰를 수정할 수 없는 상품입니다.",
        )
    )

    result = await service.edit_review(_edit_request())

    assert result.success is False
    assert result.message == "리뷰를 수정할 수 없는 상품입니다."


@pytest.mark.anyio
async def test_edit_review_fails_when_identifier_mismatch(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(
            state=CoupangReviewState.IDENTIFIER_MISMATCH,
            message="주문/상품/리뷰 식별자가 일치하지 않습니다.",
        )
    )

    result = await service.edit_review(_edit_request())

    assert result.success is False
    assert result.message == "주문/상품/리뷰 식별자가 일치하지 않습니다."


@pytest.mark.anyio
async def test_edit_review_fails_when_input_is_invalid() -> None:
    service = _make_review_service()

    result = await service.edit_review(
        ReviewEditRequest(
            order_id="22404668406",
            product_id="8825977723",
            review_id="",
            rating=0,
            text="",
        )
    )

    assert result.success is False
    assert result.message == "리뷰 ID는 비어 있을 수 없습니다."


@pytest.mark.anyio
async def test_edit_review_allows_empty_review_text(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_review_service(root_dir=tmp_path, browser=browser)
    service._edit_review_browser = AsyncMock(
        return_value=_ReviewUploadBrowserResult(state=CoupangReviewState.SUCCESS)
    )

    result = await service.edit_review(
        ReviewEditRequest(
            order_id="22404668406",
            product_id="8825977723",
            review_id="934113278",
            rating=4,
            text="",
        )
    )

    assert result.success is True
    service._edit_review_browser.assert_awaited_once()


@pytest.mark.anyio
async def test_read_review_edit_state_deserializes_cdp_success_result() -> None:
    service = _make_review_service()
    tab = _EvaluateTab(
        [
            {
                "type": "object",
                "value": [
                    ["state", {"type": "string", "value": "success"}],
                ],
            }
        ]
    )

    page_state = await service._read_review_edit_state(tab, "8825977723", "22404668406", "934113278")

    assert page_state == "success"


@pytest.mark.anyio
async def test_read_review_edit_state_only_mismatches_known_dom_identifiers() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([{"state": "success"}])

    page_state = await service._read_review_edit_state(tab, "8723409516", "", "934113278")

    assert page_state == "success"
    script = tab.evaluate_calls[0]
    assert "hasMismatchedKnownValue(productId" in script
    assert "!pageText.includes(productId)" not in script


@pytest.mark.anyio
async def test_read_review_edit_confirmation_accepts_coupang_success_modal() -> None:
    service = _make_review_service()
    tab = _EvaluateTab([{"state": "success"}])

    confirmation = await service._read_review_edit_confirmation(tab)

    assert confirmation == "success"
    script = tab.evaluate_calls[0]
    assert "구매후기가 수정되었습니다" in script
    assert "/productreview/wroteReviews" in script
