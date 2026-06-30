from __future__ import annotations

from questionary import Choice

from k_commerce_cli.base import Prompts
from k_commerce_cli.services.providers.coupang.review.type import ReviewableItem
from k_commerce_cli.services.providers.coupang.review.utils import PRODUCT_NAME_MAX_WIDTH


async def prompt_reviewable_item(
    prompts: Prompts,
    items: tuple[ReviewableItem, ...],
) -> ReviewableItem:
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
                f"{item.delivery_date}  {item.product_id}  {product_name}",
                value=item,
            )
        )

    return await prompts.select(
        "리뷰를 작성할 상품을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
        choices=choices,
    )


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
) -> EditableReviewItem:
    """조회된 작성 리뷰 목록에서 사용자가 수정할 리뷰 하나를 선택하게 합니다."""
    return await _prompt_written_review_item(
        prompts,
        items,
        message="수정할 리뷰를 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
    )


async def prompt_deletable_review_item(
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
) -> EditableReviewItem:
    """조회된 작성 리뷰 목록에서 사용자가 삭제할 리뷰 하나를 선택하게 합니다."""
    return await _prompt_written_review_item(
        prompts,
        items,
        message="삭제할 리뷰를 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
    )


async def _prompt_written_review_item(
    prompts: Prompts,
    items: tuple[EditableReviewItem, ...],
    *,
    message: str,
) -> EditableReviewItem:
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

    return await prompts.select(
        f"{message}\n"
        f"  {'#':>3}  {'상품ID':<12}  {'평점':<7}  상품명 / 후기",
        choices=choices,
    )


async def prompt_review_text(
    prompts: Prompts,
    *,
    max_length: int,
    empty_message: str,
    too_long_message: str,
    current_text: str | None = None,
) -> str:
    """허용 길이 안에서 비어 있지 않은 리뷰 본문을 입력받습니다."""
    message = "리뷰 본문을 입력하세요:"
    if current_text:
        message = f"리뷰 본문을 입력하세요 (현재: {current_text}):"

    while True:
        normalized = (await prompts.text(message)).strip()
        if not normalized:
            await prompts.print_message(empty_message)
            continue
        if len(normalized) > max_length:
            await prompts.print_message(too_long_message)
            continue
        return normalized
