from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart import common
from k_commerce_cli.commands.cart.common import (
    MSG_INTERACTIVE_CANCELLED,
    MSG_LIST_BROWSE_EXITED,
    MSG_LIST_CART,
    MSG_NO_CART_ITEMS,
    report_unless_list_success,
)
from k_commerce_cli.commands.cart.interactive import (
    await_unless_cancelled,
    run_cart_list_browse,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts


async def run_cart_list(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    try:
        cart_provider = common.get_provider(
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
    if not report_unless_list_success(terminal, result):
        return
    if not result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return

    await run_cart_list_browse(
        terminal,
        prompts,
        result.items,
        exit_message=MSG_LIST_BROWSE_EXITED,
    )
