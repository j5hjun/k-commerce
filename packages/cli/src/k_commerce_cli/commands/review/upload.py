from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Prompts, Terminal
from k_commerce_cli.commands.review.interactive import (
    await_unless_cancelled,
    prompt_rating,
    prompt_review_continue,
    prompt_review_text,
    prompt_reviewable_item,
    run_reviewable_list_browse,
)
from k_commerce_cli.commands.tool_invocation import CachedProviderFactory
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import JSONValue, ToolProviderFactory, ToolRuntimeOptions

REVIEW_TEXT_MAX_LENGTH = 800

MSG_TEXT_TOO_LONG = f"리뷰 본문은 최대 {REVIEW_TEXT_MAX_LENGTH}자까지 입력할 수 있습니다."
MSG_NO_REVIEWABLE_ITEMS = "리뷰 작성 가능한 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "리뷰 업로드를 취소했습니다."
MSG_UPLOAD_EXITED = "리뷰 업로드를 종료했습니다."
MSG_LIST_REVIEWABLE = "쿠팡 리뷰 작성 가능 목록을 조회합니다..."
MSG_LIST_BROWSE_EXITED = "리뷰 작성 가능 목록 보기를 종료했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def _format_uploaded_review(
    *,
    product_name: str,
    rating: int,
    review_text: str,
) -> str:
    return f"{product_name} / {'★' * rating}{'☆' * (5 - rating)} / {review_text}"


def _cached_provider_factory(root_dir: Path | None) -> CachedProviderFactory:
    return CachedProviderFactory(root_dir=root_dir, provider_factory=get_provider)


def _runtime_options(
    root_dir: Path | None,
    terminal: Terminal | None,
    provider_factory: ToolProviderFactory | None,
) -> ToolRuntimeOptions:
    return ToolRuntimeOptions(
        root_dir=root_dir,
        terminal=terminal,
        get_provider=provider_factory or get_provider,
    )


async def _run_interactive_upload(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    provider_factory = _cached_provider_factory(root_dir)
    try:
        provider_factory(provider, root_dir=root_dir, terminal=None)
        terminal.info(MSG_LIST_REVIEWABLE)
        provider_factory(provider, root_dir=root_dir, terminal=terminal)
        list_result = await await_unless_cancelled(
            terminal,
            invoke_tool(
                "review_list_reviewable",
                {"provider": provider},
                runtime_options=_runtime_options(root_dir, terminal, provider_factory),
            ),
            message=MSG_INTERACTIVE_CANCELLED,
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error
    if not list_result.success:
        terminal.abort(list_result.message)
    if not list_result.items:
        terminal.echo(MSG_NO_REVIEWABLE_ITEMS)
        return

    while True:
        try:
            selected_item = await prompt_reviewable_item(prompts, list_result.items)
            if selected_item is None:
                terminal.echo(MSG_UPLOAD_EXITED)
                return
            rating = await prompt_rating(prompts)
            review_text = await prompt_review_text(
                prompts,
                max_length=REVIEW_TEXT_MAX_LENGTH,
                too_long_message=MSG_TEXT_TOO_LONG,
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return

        payload: dict[str, JSONValue] = {
            "provider": provider,
            "order_id": selected_item.completed_order_vendor_item_id,
            "product_id": selected_item.product_id,
            "rating": rating,
            "text": review_text,
            "review_url": selected_item.review_url,
        }

        try:
            result = await await_unless_cancelled(
                terminal,
                invoke_tool(
                    "review_upload",
                    payload,
                    runtime_options=_runtime_options(root_dir, None, provider_factory),
                ),
                message=MSG_INTERACTIVE_CANCELLED,
            )
        except ValueError as error:
            raise click.BadParameter(str(error)) from error
        if not result.success:
            terminal.error(result.message)
            continue

        terminal.success(result.message)
        terminal.echo(
            _format_uploaded_review(
                product_name=selected_item.product_name,
                rating=rating,
                review_text=review_text,
            )
        )

        try:
            should_continue = await prompt_review_continue(
                prompts,
                message="리뷰 작성을 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return
        if not should_continue:
            terminal.echo(MSG_UPLOAD_EXITED)
            return

        terminal.info(MSG_LIST_REVIEWABLE)
        try:
            list_result = await await_unless_cancelled(
                terminal,
                invoke_tool(
                    "review_list_reviewable",
                    {"provider": provider},
                    runtime_options=_runtime_options(root_dir, terminal, provider_factory),
                ),
                message=MSG_INTERACTIVE_CANCELLED,
            )
        except ValueError as error:
            raise click.BadParameter(str(error), param_hint="provider") from error
        if not list_result.success:
            terminal.abort(list_result.message)
        if not list_result.items:
            terminal.echo(MSG_NO_REVIEWABLE_ITEMS)
            return


@click.command("upload")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List reviewable products only.")
@click.option("--root-dir", "--root_dir", type=click.Path(file_okay=False, dir_okay=True), default=None, help="Override the provider root directory.")
@click.pass_context
async def review_upload(
    ctx: click.Context,
    provider: str,
    list_only: bool,
    root_dir: str | None,
) -> None:
    if list_only:
        terminal = ctx.obj["terminal"]
        prompts = ctx.obj["prompts"]
        resolved_root_dir = _resolve_root_dir(root_dir)
        try:
            terminal.info(MSG_LIST_REVIEWABLE)
            list_result = await await_unless_cancelled(
                terminal,
                invoke_tool(
                    "review_list_reviewable",
                    {"provider": provider},
                    runtime_options=_runtime_options(resolved_root_dir, terminal, _cached_provider_factory(resolved_root_dir)),
                ),
                message=MSG_INTERACTIVE_CANCELLED,
            )
        except ValueError as error:
            raise click.BadParameter(str(error), param_hint="provider") from error
        if not list_result.success:
            terminal.abort(list_result.message)
        if not list_result.items:
            terminal.echo(MSG_NO_REVIEWABLE_ITEMS)
            return
        await run_reviewable_list_browse(
            terminal,
            prompts,
            list_result.items,
            exit_message=MSG_LIST_BROWSE_EXITED,
        )
        return

    await _run_interactive_upload(
        provider,
        _resolve_root_dir(root_dir),
        ctx.obj["terminal"],
        ctx.obj["prompts"],
    )
