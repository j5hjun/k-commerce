from pathlib import Path
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from asyncclick import ClickException
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.services.providers.coupang.review.type import (
    ListReviewableResult,
    ReviewUploadRequest,
    ReviewUploadResult,
    ReviewableItem,
)

RUNNER = CliRunner()

SAMPLE_REVIEW_URL = (
    "https://my.coupang.com/productreview/register?"
    "completedOrderVendorItemId=22404668406&"
    "productId=8825977723&"
    "deliveryDate=2026-06-15&"
    "vendorItemId=92707464866"
)


def _review_success_result() -> ReviewUploadResult:
    return ReviewUploadResult(
        provider="coupang",
        success=True,
        message="쿠팡 리뷰 업로드 성공",
        order_id="22404668406",
        product_id="8825977723",
    )


def _review_list_result() -> ListReviewableResult:
    return ListReviewableResult(
        provider="coupang",
        success=True,
        message="리뷰 작성 가능 (1건):\n\n    #  배송일        상품명",
        items=(),
    )


def _reviewable_item() -> ReviewableItem:
    return ReviewableItem(
        index=1,
        product_id="8825977723",
        product_name="포스트 아몬드후레이크",
        delivery_date="2026-03-29",
        completed_order_vendor_item_id="22404668406",
        vendor_item_id="92707464866",
        review_url=SAMPLE_REVIEW_URL,
    )


def _review_list_result_with_items() -> ListReviewableResult:
    return ListReviewableResult(
        provider="coupang",
        success=True,
        message="리뷰 작성 가능 (1건):",
        items=(_reviewable_item(),),
    )


@pytest.mark.anyio
async def test_review_upload_default_runs_interactive_flow() -> None:
    provider = Mock()
    provider.list_reviewable = AsyncMock(return_value=_review_list_result_with_items())
    provider.upload_review = AsyncMock(return_value=_review_success_result())

    with (
        patch(
            "k_commerce_cli.commands.review.upload.get_provider",
            side_effect=[provider, provider],
        ) as get_provider,
        patch(
            "k_commerce_cli.commands.review.upload.prompt_reviewable_item",
            new=AsyncMock(return_value=_reviewable_item()),
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_rating",
            new=AsyncMock(return_value=5),
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_review_text",
            new=AsyncMock(return_value="좋아요"),
        ),
    ):
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "upload",
                "coupang",
            ],
        )

    assert result.exit_code == 0
    assert get_provider.call_count == 2
    get_provider.assert_any_call("coupang", root_dir=None, terminal=ANY)
    get_provider.assert_any_call("coupang", root_dir=None, terminal=None)
    provider.list_reviewable.assert_awaited_once_with()
    provider.upload_review.assert_awaited_once_with(
        ReviewUploadRequest(
            order_id="22404668406",
            product_id="8825977723",
            rating=5,
            text="좋아요",
            review_url=SAMPLE_REVIEW_URL,
        ),
    )


@pytest.mark.anyio
async def test_review_upload_interactive_cancel_raises_click_exception() -> None:
    provider = Mock()
    provider.list_reviewable = AsyncMock(return_value=_review_list_result_with_items())

    with (
        patch(
            "k_commerce_cli.commands.review.upload.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_reviewable_item",
            new=AsyncMock(side_effect=KeyboardInterrupt),
        ),
    ):
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "upload",
                "coupang",
            ],
        )

    assert result.exit_code == 1
    assert "리뷰 업로드를 취소했습니다." in result.output
    provider.upload_review.assert_not_called()


@pytest.mark.anyio
async def test_review_list_prints_reviewable_items() -> None:
    provider = Mock()
    provider.list_reviewable = AsyncMock(return_value=_review_list_result())

    with patch(
        "k_commerce_cli.commands.review.list.get_provider",
        return_value=provider,
    ) as get_provider:
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "list",
                "coupang",
            ],
        )

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.list_reviewable.assert_awaited_once_with()


@pytest.mark.anyio
async def test_review_list_passes_root_dir(tmp_path: Path) -> None:
    provider = Mock()
    provider.list_reviewable = AsyncMock(return_value=_review_list_result())

    with patch(
        "k_commerce_cli.commands.review.list.get_provider",
        return_value=provider,
    ) as get_provider:
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "list",
                "coupang",
                "--root-dir",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.list_reviewable.assert_awaited_once_with()


@pytest.mark.anyio
async def test_review_upload_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.commands.review.upload.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ) as get_provider:
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "upload",
                "invalid",
            ],
        )

    assert result.exit_code == 2
    assert "Invalid value: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid", root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_review_upload_failure_raises_click_exception() -> None:
    provider = Mock()
    provider.list_reviewable = AsyncMock(return_value=_review_list_result_with_items())
    provider.upload_review = AsyncMock(
        side_effect=ClickException("쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."),
    )

    with (
        patch(
            "k_commerce_cli.commands.review.upload.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_reviewable_item",
            new=AsyncMock(return_value=_reviewable_item()),
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_rating",
            new=AsyncMock(return_value=5),
        ),
        patch(
            "k_commerce_cli.commands.review.upload.prompt_review_text",
            new=AsyncMock(return_value="좋아요"),
        ),
    ):
        result = await RUNNER.invoke(
            app,
            [
                "review",
                "upload",
                "coupang",
            ],
        )

    assert result.exit_code == 1
    assert "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요." in result.output
