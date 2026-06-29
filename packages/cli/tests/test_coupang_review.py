from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.providers.coupang.review.service import (
    CoupangReviewService,
    _ListReviewableBrowserResult,
    _ReviewUploadBrowserResult,
    _ReviewableItemData,
    deserialize_evaluate_result,
)
from k_commerce_cli.services.providers.coupang.review.state import CoupangReviewState
from k_commerce_cli.services.providers.coupang.review.utils import (
    build_review_register_url,
    format_reviewable_list,
)
from k_commerce_cli.services.registry import get_provider, list_providers
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.providers.coupang.review.type import (
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
        self.close = AsyncMock()
        self.select = AsyncMock(return_value=None)


class _EvaluateTab:
    def __init__(self, payloads: list[object]) -> None:
        self._payloads = list(payloads)

    async def evaluate(self, _script: str, _args=None):
        if not self._payloads:
            return []
        return self._payloads.pop(0)


def _make_review_service(
    *,
    root_dir: Path | None = None,
    browser: _BrowserSpy | None = None,
) -> CoupangReviewService:
    resolved_root = root_dir if root_dir is not None else Path.home() / ".k-commerce"
    return CoupangReviewService(
        provider_name="coupang",
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


def test_build_review_register_url() -> None:
    assert build_review_register_url(
        completed_order_vendor_item_id="22404668406",
        product_id="8825977723",
        delivery_date="2026-06-15",
        vendor_item_id="92707464866",
    ) == SAMPLE_REVIEW_URL


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

    page_state = await service._read_review_register_state(tab, "8825977723")

    assert page_state == "success"


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
async def test_list_reviewable_fails_when_session_is_missing(tmp_path: Path) -> None:
    service = _make_review_service()

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

    result = await service.upload_review(_request())

    assert result.success is True
    assert result.message == "쿠팡 리뷰 업로드 성공"
    assert result.order_id == "22404668406"
    assert result.product_id == "8825977723"
    browser.launch.assert_awaited_once()
    service._upload_review_browser.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_upload_review_fails_when_session_is_missing(tmp_path: Path) -> None:
    service = _make_review_service()

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
