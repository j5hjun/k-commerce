from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.review.interactive import (
    prompt_editable_review_item,
    prompt_rating,
    prompt_review_text,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import ReviewEditRequest

REVIEW_TEXT_MAX_LENGTH = 800

MSG_TEXT_EMPTY = "리뷰 본문은 비어 있을 수 없습니다."
MSG_TEXT_TOO_LONG = f"리뷰 본문은 최대 {REVIEW_TEXT_MAX_LENGTH}자까지 입력할 수 있습니다."
MSG_NO_EDITABLE_ITEMS = "수정 가능한 작성 리뷰가 없습니다."
MSG_INTERACTIVE_CANCELLED = "리뷰 수정을 취소했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


async def _run_interactive_edit(
    provider: str,
    root_dir,
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
        raise click.BadParameter(str(error), param_hint="provider") from error

    list_result = await list_provider.list_editable()

    if not list_result.success:
        terminal.abort(list_result.message)
    if not list_result.items:
        terminal.abort(MSG_NO_EDITABLE_ITEMS)

    try:
        selected_item = await prompt_editable_review_item(prompts, list_result.items)
        rating = await prompt_rating(prompts, current_rating=selected_item.rating)
        review_text = await prompt_review_text(
            prompts,
            max_length=REVIEW_TEXT_MAX_LENGTH,
            empty_message=MSG_TEXT_EMPTY,
            too_long_message=MSG_TEXT_TOO_LONG,
            current_text=selected_item.review_text,
        )
    except KeyboardInterrupt:
        terminal.abort(MSG_INTERACTIVE_CANCELLED)

    await review_provider.edit_review(
        ReviewEditRequest(
            order_id=selected_item.order_id,
            product_id=selected_item.product_id,
            review_id=selected_item.review_id,
            rating=rating,
            text=review_text,
        )
    )


@click.command("edit")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List editable reviews only.")
@click.option(
    "--root-dir",
    "--root_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider root directory.",
)
@click.pass_context
async def review_edit(
    ctx: click.Context,
    provider: str,
    list_only: bool,
    root_dir: str | None,
) -> None:
    resolved_root_dir = _resolve_root_dir(root_dir)
    if list_only:
        try:
            review_provider = get_provider(
                provider,
                root_dir=resolved_root_dir,
                terminal=ctx.obj["terminal"],
            )
        except ValueError as error:
            raise click.BadParameter(str(error), param_hint="provider") from error
        await review_provider.list_editable()
        return

    await _run_interactive_edit(
        provider,
        resolved_root_dir,
        ctx.obj["terminal"],
        ctx.obj["prompts"],
    )
