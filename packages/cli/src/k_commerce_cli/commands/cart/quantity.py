from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart import common, interactive
from k_commerce_cli.commands.cart.common import (
    MSG_INTERACTIVE_CANCELLED,
    MSG_LIST_CART,
    MSG_NO_CART_ITEMS,
    MSG_QUANTITY_UPDATE_EXITED,
    invoke_cart_list,
    invoke_cart_update_quantity,
    report_unless_list_success,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.types import CartItem, CartQuantityUpdateRequest


def _format_quantity_update_summary(item: CartItem, quantity: int) -> str:
    option_text = item.option_text or "-"
    return f"{item.product_name} / {option_text} / {quantity}개"


async def run_quantity_update(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    provider_factory = common.cached_provider_factory(root_dir)
    try:
        provider_factory(provider, root_dir=root_dir, terminal=None)
        terminal.info(MSG_LIST_CART)
        provider_factory(provider, root_dir=root_dir, terminal=terminal)
        list_result = await interactive.await_unless_cancelled(
            terminal,
            invoke_cart_list(provider, root_dir, terminal, provider_factory),
            message=MSG_INTERACTIVE_CANCELLED,
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error
    if not report_unless_list_success(terminal, list_result):
        return
    if not list_result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return

    while True:
        try:
            selected_item = await interactive.prompt_cart_item(
                prompts,
                list_result.items,
                selection_prefix="수량을 수정할 상품을 선택하세요",
            )
            if selected_item is None or not isinstance(selected_item, CartItem):
                terminal.echo(MSG_QUANTITY_UPDATE_EXITED)
                return
            quantity = await interactive.prompt_quantity(
                prompts, current_quantity=selected_item.quantity
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return

        update_result = await interactive.await_unless_cancelled(
            terminal,
            invoke_cart_update_quantity(
                provider,
                root_dir,
                CartQuantityUpdateRequest(
                    product_id=selected_item.product_id,
                    vendor_item_id=selected_item.vendor_item_id,
                    item_id=selected_item.item_id,
                    quantity=quantity,
                ),
                provider_factory,
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
            should_continue = await interactive.prompt_cart_continue(
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
        list_result = await interactive.await_unless_cancelled(
            terminal,
            invoke_cart_list(provider, root_dir, terminal, provider_factory),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not report_unless_list_success(terminal, list_result):
            return
        if not list_result.items:
            terminal.echo(MSG_NO_CART_ITEMS)
            return
