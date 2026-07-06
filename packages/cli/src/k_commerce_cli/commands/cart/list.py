from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.common import (
    MSG_INTERACTIVE_CANCELLED,
    MSG_LIST_BROWSE_EXITED,
    MSG_LIST_CART,
    MSG_NO_CART_ITEMS,
    invoke_cart_list,
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
        terminal.info(MSG_LIST_CART)
        result = await await_unless_cancelled(
            terminal,
            invoke_cart_list(provider, root_dir, terminal),
            message=MSG_INTERACTIVE_CANCELLED,
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error
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
