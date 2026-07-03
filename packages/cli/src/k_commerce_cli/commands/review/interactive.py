from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Literal, TypeVar

import asyncclick as click
from questionary import Choice

from k_commerce_cli.base import Prompts, Terminal
from k_commerce_cli.services.types import EditableReviewItem, ReviewableItem
from k_commerce_cli.services.providers.coupang.review.utils import (
    PRODUCT_NAME_MAX_WIDTH,
    REVIEW_TEXT_MAX_WIDTH,
    format_rating,
)

ListDetailAction = Literal["back", "exit"]

_EXIT_REVIEW_SELECTION = object()
_CONTINUE_REVIEW_SELECTION = object()
_BACK_TO_LIST = object()
_EXIT_LIST_BROWSE = object()

T = TypeVar("T")

# questionary select가 각 항목 앞에 붙이는 포인터/선택 표시(»○   ) 너비
_QUESTIONARY_SELECT_PREFIX = "     "

_REVIEW_LIST_HEADER = (
    f"{_QUESTIONARY_SELECT_PREFIX}{'No':>3}  {'배송일':<12}  {'상품ID':<12}  상품명"
)
_WRITTEN_REVIEW_LIST_HEADER = (
    f"{_QUESTIONARY_SELECT_PREFIX}{'No':>3}  {'상품ID':<12}  {'평점':<7}  상품명 / 후기"
)


def _review_selection_prompt(prefix: str, count: int, *, browse: bool = False) -> str:
    enter_hint = "Enter로 상세 보기" if browse else "Enter 선택"
    return f"{prefix} (전체 {count}개, ↑↓ 이동, {enter_hint}, Ctrl+C 취소):"


async def await_unless_cancelled(
    terminal: Terminal,
    awaitable: Awaitable[T],
    *,
    message: str,
) -> T:
    """브라우저 대기 중 Ctrl+C가 들어오면 traceback 없이 취소 메시지로 종료합니다."""
    try:
        return await awaitable
    except (KeyboardInterrupt, asyncio.CancelledError):
        terminal.echo(message)
        raise click.exceptions.Exit(0) from None


async def prompt_reviewable_item(
    prompts: Prompts,
    items: tuple[ReviewableItem, ...],
    *,
    selection_prefix: str = "리뷰를 작성할 상품을 선택하세요",
    browse: bool = False,
) -> ReviewableItem | None:
    """조회된 리뷰 작성 가능 목록에서 사용자가 상품 하나를 선택하게 합니다."""
    choices: list[Choice] = []
    for item in items:
        product_name = (
            item.product_name
            if len(item.product_name) <= PRODUCT_NAME_MAX_WIDTH
            else f"{item.product_name[: PRODUCT_NAME_MAX_WIDTH - 3]}..."
        )
        choices.append(
            Choice(
                f"{item.index:>3}  {item.delivery_date:<12}  {item.product_id:<12}  {product_name}",
                value=item,
            )
        )
    choices.append(Choice("나가기", value=_EXIT_REVIEW_SELECTION))

    selected = await prompts.select(
        f"{_review_selection_prompt(selection_prefix, len(items), browse=browse)}\n"
        f"{_REVIEW_LIST_HEADER}",
        choices=choices,
    )
    if selected is _EXIT_REVIEW_SELECTION or selected == "나가기":
        return None
    return selected


async def prompt_rating(prompts: Prompts, *, current_rating: int | None = None) -> int:
    """사용자가 1-5점 별점을 선택하게 합니다."""
    message = "별점을 선택하세요 (↑↓ 이동, Enter 선택):"
    if current_rating is not None and 1 <= current_rating <= 5:
        message = f"별점을 선택하세요 (현재: {format_rating(current_rating)} {current_rating}점, ↑↓ 이동, Enter 선택):"

    return await prompts.select(
        message,
        choices=[
            Choice(f"★★★★★  5점{'  (현재)' if current_rating == 5 else ''}", value=5),
            Choice(f"★★★★☆  4점{'  (현재)' if current_rating == 4 else ''}", value=4),
            Choice(f"★★★☆☆  3점{'  (현재)' if current_rating == 3 else ''}", value=3),
            Choice(f"★★☆☆☆  2점{'  (현재)' if current_rating == 2 else ''}", value=2),
            Choice(f"★☆☆☆☆  1점{'  (현재)' if current_rating == 1 else ''}", value=1),
        ],
    )


async def prompt_editable_review_item(
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    selection_prefix: str = "수정할 리뷰를 선택하세요",
    browse: bool = False,
) -> EditableReviewItem | None:
    """조회된 작성 리뷰 목록에서 사용자가 수정할 리뷰 하나를 선택하게 합니다."""
    return await _prompt_written_review_item(
        prompts,
        items,
        message=_review_selection_prompt(selection_prefix, len(items), browse=browse),
    )


async def prompt_deletable_review_item(
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    selection_prefix: str = "삭제할 리뷰를 선택하세요",
    browse: bool = False,
) -> EditableReviewItem | None:
    """조회된 작성 리뷰 목록에서 사용자가 삭제할 리뷰 하나를 선택하게 합니다."""
    return await _prompt_written_review_item(
        prompts,
        items,
        message=_review_selection_prompt(selection_prefix, len(items), browse=browse),
    )


async def _prompt_written_review_item(
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    message: str,
) -> EditableReviewItem | None:
    choices: list[Choice] = []
    for item in items:
        product_name = (
            item.product_name
            if len(item.product_name) <= PRODUCT_NAME_MAX_WIDTH
            else f"{item.product_name[: PRODUCT_NAME_MAX_WIDTH - 3]}..."
        )
        review_text = (
            item.review_text
            if len(item.review_text) <= REVIEW_TEXT_MAX_WIDTH
            else f"{item.review_text[: REVIEW_TEXT_MAX_WIDTH - 3]}..."
        )
        choices.append(
            Choice(
                f"{item.index:>3}  {item.product_id or '-':<12}  {format_rating(item.rating):<7}  {product_name} / {review_text}",
                value=item,
            )
        )
    choices.append(Choice("나가기", value=_EXIT_REVIEW_SELECTION))

    selected = await prompts.select(
        f"{message}\n{_WRITTEN_REVIEW_LIST_HEADER}",
        choices=choices,
    )
    if selected is _EXIT_REVIEW_SELECTION or selected == "나가기":
        return None
    return selected


async def prompt_review_text(
    prompts: Prompts,
    *,
    max_length: int,
    too_long_message: str,
    current_text: str | None = None,
) -> str:
    """허용 길이 안에서 리뷰 본문을 입력받습니다."""
    message = "리뷰 본문을 입력하세요:"
    if current_text:
        message = f"리뷰 본문을 입력하세요 (현재: {current_text}):"

    while True:
        normalized = (await prompts.text(message)).strip()
        if len(normalized) > max_length:
            await prompts.print_message(too_long_message)
            continue
        return normalized


async def prompt_review_continue(
    prompts: Prompts,
    *,
    message: str,
) -> bool:
    selected = await prompts.select(
        message,
        choices=[
            Choice("다른 리뷰 선택", value=_CONTINUE_REVIEW_SELECTION),
            Choice("나가기", value=_EXIT_REVIEW_SELECTION),
        ],
    )
    return selected is _CONTINUE_REVIEW_SELECTION


def format_reviewable_detail(item: ReviewableItem) -> str:
    """리뷰 작성 가능 상품의 전체 상세 정보를 포맷합니다."""
    lines = [
        ("No", str(item.index)),
        ("배송일", item.delivery_date),
        ("상품ID", item.product_id),
        ("상품명", item.product_name),
        ("주문ID", item.completed_order_vendor_item_id or "-"),
        ("벤더상품ID", item.vendor_item_id or "-"),
    ]
    return _format_labeled_detail(lines)


def format_written_review_detail(
    item: EditableReviewItem,
    *,
    show_review_id: bool,
) -> str:
    """작성 리뷰의 전체 상세 정보를 포맷합니다."""
    lines = [
        ("No", str(item.index)),
        ("상품ID", item.product_id or "-"),
        ("평점", f"{format_rating(item.rating)} ({item.rating}점)" if 1 <= item.rating <= 5 else "-"),
        ("상품명", item.product_name),
        ("후기", item.review_text),
    ]
    if show_review_id:
        lines.insert(2, ("리뷰ID", item.review_id))
    return _format_labeled_detail(lines)


def _format_labeled_detail(lines: list[tuple[str, str]]) -> str:
    return "\n".join(f"{label}: {value}" for label, value in lines)


async def prompt_list_detail_action(prompts: Prompts) -> ListDetailAction:
    """상세 보기 후 돌아가기 또는 나가기를 선택하게 합니다."""
    selected = await prompts.select(
        "다음 작업을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=[
            Choice("돌아가기", value=_BACK_TO_LIST),
            Choice("나가기", value=_EXIT_LIST_BROWSE),
        ],
    )
    if selected is _BACK_TO_LIST:
        return "back"
    return "exit"


async def run_reviewable_list_browse(
    terminal: Terminal,
    prompts: Prompts,
    items: tuple[ReviewableItem, ...],
    *,
    exit_message: str,
) -> None:
    """리뷰 작성 가능 목록을 조회한 뒤 상세 보기 루프를 실행합니다."""
    while True:
        try:
            selected_item = await prompt_reviewable_item(
                prompts,
                items,
                selection_prefix="상세 보기할 상품을 고르세요",
                browse=True,
            )
            if selected_item is None:
                terminal.echo(exit_message)
                return
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return

        terminal.echo(format_reviewable_detail(selected_item))

        try:
            action = await prompt_list_detail_action(prompts)
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return
        if action == "exit":
            terminal.echo(exit_message)
            return


async def run_editable_list_browse(
    terminal: Terminal,
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    exit_message: str,
) -> None:
    """수정 가능한 작성 리뷰 목록을 조회한 뒤 상세 보기 루프를 실행합니다."""
    while True:
        try:
            selected_item = await prompt_editable_review_item(
                prompts,
                items,
                selection_prefix="상세 보기할 리뷰를 고르세요",
                browse=True,
            )
            if selected_item is None:
                terminal.echo(exit_message)
                return
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return

        terminal.echo(format_written_review_detail(selected_item, show_review_id=True))

        try:
            action = await prompt_list_detail_action(prompts)
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return
        if action == "exit":
            terminal.echo(exit_message)
            return


async def run_deletable_list_browse(
    terminal: Terminal,
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    exit_message: str,
) -> None:
    """삭제 가능한 작성 리뷰 목록을 조회한 뒤 상세 보기 루프를 실행합니다."""
    while True:
        try:
            selected_item = await prompt_deletable_review_item(
                prompts,
                items,
                selection_prefix="상세 보기할 리뷰를 고르세요",
                browse=True,
            )
            if selected_item is None:
                terminal.echo(exit_message)
                return
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return

        terminal.echo(format_written_review_detail(selected_item, show_review_id=False))

        try:
            action = await prompt_list_detail_action(prompts)
        except KeyboardInterrupt:
            terminal.echo(exit_message)
            return
        if action == "exit":
            terminal.echo(exit_message)
            return
