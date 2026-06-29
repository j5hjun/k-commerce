from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.terminal.prompts import Prompts
from k_commerce_cli.commands.review.interactive import (
    prompt_rating,
    prompt_review_text,
    prompt_reviewable_item,
)
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import ReviewUploadRequest

REVIEW_TEXT_MAX_LENGTH = 800

MSG_TEXT_EMPTY = "리뷰 본문은 비어 있을 수 없습니다."
MSG_TEXT_TOO_LONG = f"리뷰 본문은 최대 {REVIEW_TEXT_MAX_LENGTH}자까지 입력할 수 있습니다."
MSG_NO_REVIEWABLE_ITEMS = "리뷰 작성 가능한 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "리뷰 업로드를 취소했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


async def _run_interactive_upload(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    try:
        review_provider = get_provider(
            provider,
            root_dir=root_dir,
            terminal=terminal,
        )
        list_provider = get_provider(
            provider,
            root_dir=root_dir,
            terminal=None,
        )
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    list_result = await list_provider.list_reviewable()

    if not list_result.success:
        terminal.abort(list_result.message)
    if not list_result.items:
        terminal.abort(MSG_NO_REVIEWABLE_ITEMS)

    try:
        selected_item = await prompt_reviewable_item(prompts, list_result.items)
        rating = await prompt_rating(prompts)
        review_text = await prompt_review_text(
            prompts,
            max_length=REVIEW_TEXT_MAX_LENGTH,
            empty_message=MSG_TEXT_EMPTY,
            too_long_message=MSG_TEXT_TOO_LONG,
        )
    except KeyboardInterrupt:
        terminal.abort(MSG_INTERACTIVE_CANCELLED)

    request = ReviewUploadRequest(
        order_id=selected_item.completed_order_vendor_item_id,
        product_id=selected_item.product_id,
        rating=rating,
        text=review_text,
        review_url=selected_item.review_url,
    )

    try:
        await review_provider.upload_review(request)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error


@click.command("upload")
@click.argument("provider")
@click.option("--root-dir", "--root_dir", type=click.Path(file_okay=False, dir_okay=True), default=None, help="Override the provider root directory.")
@click.pass_context
async def review_upload(ctx: click.Context, provider: str, root_dir: str | None) -> None:
    await _run_interactive_upload(
        provider,
        _resolve_root_dir(root_dir),
        ctx.obj["terminal"],
        ctx.obj["prompts"],
    )
