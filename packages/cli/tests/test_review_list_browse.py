from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.review.interactive import (
    _review_selection_prompt,
    format_reviewable_detail,
    format_written_review_detail,
    run_deletable_list_browse,
    run_editable_list_browse,
    run_reviewable_list_browse,
)
from k_commerce_cli.prompts import QuestionaryPrompts
from k_commerce_cli.services.types import EditableReviewItem, ReviewableItem

SAMPLE_REVIEW_URL = (
    "https://my.coupang.com/productreview/register?"
    "completedOrderVendorItemId=22404668406&productId=8825977723"
)


def _reviewable_item() -> ReviewableItem:
    return ReviewableItem(
        index=1,
        product_id="8825977723",
        product_name="포스트 아몬드후레이크 620g, 620g, 1개",
        delivery_date="2026-03-29",
        completed_order_vendor_item_id="22404668406",
        vendor_item_id="92707464866",
        review_url=SAMPLE_REVIEW_URL,
    )


def _editable_review_item() -> EditableReviewItem:
    return EditableReviewItem(
        index=2,
        review_id="934113278",
        product_id="8825977723",
        order_id="22404668406",
        product_name="포스트 아몬드후레이크",
        rating=5,
        review_text="예전 리뷰 본문 전체",
        modify_url="https://my.coupang.com/productreview/wroteReviews/934113278/modify?page=1",
    )


def test_review_selection_prompt_mentions_detail_for_browse_mode() -> None:
    browse_prompt = _review_selection_prompt("상세 보기할 리뷰를 고르세요", 3, browse=True)
    action_prompt = _review_selection_prompt("삭제할 리뷰를 선택하세요", 3)

    assert "상세 보기할 리뷰를 고르세요" in browse_prompt
    assert "Enter로 상세 보기" in browse_prompt
    assert "선택하세요" not in browse_prompt
    assert "Enter 선택" in action_prompt
    assert "Enter로 상세 보기" not in action_prompt


def test_format_reviewable_detail_shows_full_fields() -> None:
    output = format_reviewable_detail(_reviewable_item())

    assert "No: 1" in output
    assert "배송일: 2026-03-29" in output
    assert "상품ID: 8825977723" in output
    assert "포스트 아몬드후레이크" in output


def test_format_written_review_detail_hides_review_id_for_delete() -> None:
    output = format_written_review_detail(_editable_review_item(), show_review_id=False)

    assert "리뷰ID" not in output
    assert "934113278" not in output
    assert "예전 리뷰 본문 전체" in output


def test_format_written_review_detail_shows_empty_review_text() -> None:
    item = replace(_editable_review_item(), review_text="")
    output = format_written_review_detail(item, show_review_id=False)

    assert "후기: " in output
    assert "후기: -" not in output


def test_format_written_review_detail_shows_review_id_for_edit() -> None:
    output = format_written_review_detail(_editable_review_item(), show_review_id=True)

    assert "리뷰ID: 934113278" in output


@pytest.mark.anyio
async def test_run_reviewable_list_browse_shows_detail_then_exits() -> None:
    terminal = Mock(spec=Terminal)
    terminal.echo = Mock()
    terminal.abort = Mock(side_effect=SystemExit)
    prompts = Mock(spec=QuestionaryPrompts)

    with (
        patch(
            "k_commerce_cli.commands.review.interactive.prompt_reviewable_item",
            new=AsyncMock(return_value=_reviewable_item()),
        ),
        patch(
            "k_commerce_cli.commands.review.interactive.prompt_list_detail_action",
            new=AsyncMock(return_value="exit"),
        ),
    ):
        await run_reviewable_list_browse(
            terminal,
            prompts,
            (_reviewable_item(),),
            exit_message="종료",
        )

    terminal.echo.assert_any_call(format_reviewable_detail(_reviewable_item()))
    terminal.echo.assert_any_call("종료")


@pytest.mark.anyio
async def test_run_editable_list_browse_returns_to_list_on_back() -> None:
    terminal = Mock(spec=Terminal)
    terminal.echo = Mock()
    prompts = Mock(spec=QuestionaryPrompts)
    item = _editable_review_item()

    with (
        patch(
            "k_commerce_cli.commands.review.interactive.prompt_editable_review_item",
            new=AsyncMock(side_effect=[item, None]),
        ),
        patch(
            "k_commerce_cli.commands.review.interactive.prompt_list_detail_action",
            new=AsyncMock(return_value="back"),
        ),
    ):
        await run_editable_list_browse(
            terminal,
            prompts,
            (item,),
            exit_message="종료",
        )

    assert terminal.echo.call_args_list[-1] == (("종료",),)


@pytest.mark.anyio
async def test_run_deletable_list_browse_exits_from_selection() -> None:
    terminal = Mock(spec=Terminal)
    terminal.echo = Mock()
    prompts = Mock(spec=QuestionaryPrompts)

    with patch(
        "k_commerce_cli.commands.review.interactive.prompt_deletable_review_item",
        new=AsyncMock(return_value=None),
    ):
        await run_deletable_list_browse(
            terminal,
            prompts,
            (_editable_review_item(),),
            exit_message="종료",
        )

    terminal.echo.assert_called_once_with("종료")
