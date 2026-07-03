from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.review.interactive import (
    await_unless_cancelled,
    prompt_deletable_review_item,
    prompt_review_continue,
    run_deletable_list_browse,
)
from k_commerce_cli.services.providers.coupang.review.utils import format_rating
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import ReviewDeleteRequest

MSG_NO_DELETABLE_ITEMS = "삭제 가능한 작성 리뷰가 없습니다."
MSG_INTERACTIVE_CANCELLED = "리뷰 삭제를 취소했습니다."
MSG_LIST_DELETABLE = "쿠팡 리뷰 삭제 가능 목록을 조회합니다..."
MSG_DELETE_EXITED = "리뷰 삭제를 종료했습니다."
MSG_LIST_BROWSE_EXITED = "리뷰 삭제 가능 목록 보기를 종료했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def _format_deleted_review(
    *,
    product_name: str,
    rating: int,
    review_text: str,
) -> str:
    return f"{product_name} / {format_rating(rating)} / {review_text}"


async def _run_interactive_delete(
    provider: str,
    root_dir,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    try:
        review_provider = get_provider(
            provider,
            root_dir=root_dir,
            terminal=None,
        )
        list_provider = get_provider(
            provider,
            root_dir=root_dir,
            terminal=terminal,
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    terminal.info(MSG_LIST_DELETABLE)
    list_result = await await_unless_cancelled(
        terminal,
        list_provider.list_editable(),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    if not list_result.success:
        terminal.abort(list_result.message)
    if not list_result.items:
        terminal.echo(MSG_NO_DELETABLE_ITEMS)
        return

    while True:
        try:
            selected_item = await prompt_deletable_review_item(
                prompts,
                list_result.items,
            )
            if selected_item is None:
                terminal.echo(MSG_DELETE_EXITED)
                return
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return

        result = await await_unless_cancelled(
            terminal,
            review_provider.delete_review(
                ReviewDeleteRequest(
                    order_id=selected_item.order_id,
                    product_id=selected_item.product_id,
                    review_id=selected_item.review_id,
                )
            ),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not result.success:
            terminal.error(result.message)
            continue

        terminal.success(result.message)
        terminal.echo(
            _format_deleted_review(
                product_name=selected_item.product_name,
                rating=selected_item.rating,
                review_text=selected_item.review_text,
            )
        )

        try:
            should_continue = await prompt_review_continue(
                prompts,
                message="리뷰 삭제를 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return
        if not should_continue:
            terminal.echo(MSG_DELETE_EXITED)
            return

        terminal.info(MSG_LIST_DELETABLE)
        list_result = await await_unless_cancelled(
            terminal,
            list_provider.list_editable(),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not list_result.success:
            terminal.abort(list_result.message)
        if not list_result.items:
            terminal.echo(MSG_NO_DELETABLE_ITEMS)
            return


@click.command("delete")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List deletable reviews only.")
@click.option(
    "--root-dir",
    "--root_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider root directory.",
)
@click.pass_context
async def review_delete(
    ctx: click.Context,
    provider: str,
    list_only: bool,
    root_dir: str | None,
) -> None:
    resolved_root_dir = _resolve_root_dir(root_dir)
    if list_only:
        terminal = ctx.obj["terminal"]
        prompts = ctx.obj["prompts"]
        try:
            review_provider = get_provider(
                provider,
                root_dir=resolved_root_dir,
                terminal=terminal,
            )
        except ValueError as error:
            raise click.BadParameter(str(error), param_hint="provider") from error
        terminal.info(MSG_LIST_DELETABLE)
        list_result = await await_unless_cancelled(
            terminal,
            review_provider.list_editable(),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not list_result.success:
            terminal.abort(list_result.message)
        if not list_result.items:
            terminal.echo(MSG_NO_DELETABLE_ITEMS)
            return
        await run_deletable_list_browse(
            terminal,
            prompts,
            list_result.items,
            exit_message=MSG_LIST_BROWSE_EXITED,
        )
        return

    await _run_interactive_delete(
        provider,
        resolved_root_dir,
        ctx.obj["terminal"],
        ctx.obj["prompts"],
    )
