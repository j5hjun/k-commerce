from __future__ import annotations

from questionary import Choice

from k_commerce_cli.terminal.prompts import Prompts
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


async def prompt_rating(prompts: Prompts) -> int:
    """사용자가 1-5점 별점을 선택하게 합니다."""
    return await prompts.select(
        "별점을 선택하세요 (↑↓ 이동, Enter 선택):",
        choices=[
            Choice("★★★★★  5점", value=5),
            Choice("★★★★☆  4점", value=4),
            Choice("★★★☆☆  3점", value=3),
            Choice("★★☆☆☆  2점", value=2),
            Choice("★☆☆☆☆  1점", value=1),
        ],
    )


async def prompt_review_text(
    prompts: Prompts,
    *,
    max_length: int,
    empty_message: str,
    too_long_message: str,
) -> str:
    """허용 길이 안에서 비어 있지 않은 리뷰 본문을 입력받습니다."""
    while True:
        normalized = (await prompts.text("리뷰 본문을 입력하세요:")).strip()
        if not normalized:
            await prompts.print_message(empty_message)
            continue
        if len(normalized) > max_length:
            await prompts.print_message(too_long_message)
            continue
        return normalized
