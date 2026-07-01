from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import (
    await_unless_cancelled,
    prompt_cart_continue,
    prompt_cart_item,
    prompt_quantity,
    run_cart_list_browse,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import CartItem, CartQuantityUpdateRequest, ListCartResult

MSG_NO_CART_ITEMS = "장바구니에 담긴 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "장바구니 작업을 취소했습니다."
MSG_QUANTITY_UPDATE_EXITED = "장바구니 수량 수정을 종료했습니다."
MSG_LIST_CART = "쿠팡 장바구니 목록을 조회합니다..."
MSG_LIST_BROWSE_EXITED = "장바구니 목록 보기를 종료했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def _format_quantity_update_summary(item: CartItem, quantity: int) -> str:
    option_text = item.option_text or "-"
    return f"{item.product_name} / {option_text} / {quantity}개"


def _abort_unless_list_success(terminal: Terminal, result: ListCartResult) -> None:
    if not result.success:
        terminal.abort(result.message)


async def _run_quantity_update(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    try:
        update_provider = get_provider(
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

    terminal.info(MSG_LIST_CART)
    list_result = await await_unless_cancelled(
        terminal,
        list_provider.list_cart(),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    _abort_unless_list_success(terminal, list_result)
    if not list_result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return

    while True:
        try:
            selected_item = await prompt_cart_item(
                prompts,
                list_result.items,
                selection_prefix="수량을 수정할 상품을 선택하세요",
            )
            if selected_item is None or not isinstance(selected_item, CartItem):
                terminal.echo(MSG_QUANTITY_UPDATE_EXITED)
                return
            quantity = await prompt_quantity(prompts, current_quantity=selected_item.quantity)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return

        update_result = await await_unless_cancelled(
            terminal,
            update_provider.update_cart_quantity(
                CartQuantityUpdateRequest(
                    product_id=selected_item.product_id,
                    vendor_item_id=selected_item.vendor_item_id,
                    item_id=selected_item.item_id,
                    quantity=quantity,
                )
            ),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not update_result.success:
            terminal.error(update_result.message)
            continue

        terminal.success(update_result.message)
        if update_result.notice:
            terminal.warn(update_result.notice)
        terminal.echo(_format_quantity_update_summary(selected_item, update_result.quantity))

        try:
            should_continue = await prompt_cart_continue(
                prompts,
                message="수량 수정을 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return
        if not should_continue:
            terminal.echo(MSG_QUANTITY_UPDATE_EXITED)
            return

        terminal.info(MSG_LIST_CART)
        list_result = await await_unless_cancelled(
            terminal,
            list_provider.list_cart(),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        _abort_unless_list_success(terminal, list_result)
        if not list_result.items:
            terminal.echo(MSG_NO_CART_ITEMS)
            return


async def _run_cart_list(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    try:
        cart_provider = get_provider(
            provider,
            root_dir=root_dir,
            terminal=terminal,
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    terminal.info(MSG_LIST_CART)
    result = await await_unless_cancelled(
        terminal,
        cart_provider.list_cart(),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    _abort_unless_list_success(terminal, result)
    if not result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return

    await run_cart_list_browse(
        terminal,
        prompts,
        result.items,
        exit_message=MSG_LIST_BROWSE_EXITED,
    )


@click.command("cart")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List cart products only.")
@click.option("--quantity", "quantity_mode", is_flag=True, help="Update a cart product quantity.")
@click.option(
    "--root-dir",
    "--root_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider root directory.",
)
@click.pass_context
async def cart(
    ctx: click.Context,
    provider: str,
    list_only: bool,
    quantity_mode: bool,
    root_dir: str | None,
) -> None:
    resolved_root_dir = _resolve_root_dir(root_dir)
    if list_only and quantity_mode:
        raise click.UsageError("--list와 --quantity는 함께 사용할 수 없습니다.")

    if quantity_mode:
        await _run_quantity_update(
            provider,
            resolved_root_dir,
            ctx.obj["terminal"],
            ctx.obj["prompts"],
        )
        return

    await _run_cart_list(
        provider,
        resolved_root_dir,
        ctx.obj["terminal"],
        ctx.obj["prompts"],
    )
