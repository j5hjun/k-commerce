from pathlib import Path
from typing import Literal

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart import common, interactive
from k_commerce_cli.commands.cart.common import (
    MSG_DELETE_EXITED,
    MSG_INTERACTIVE_CANCELLED,
    MSG_LIST_CART,
    MSG_NO_CART_ITEMS,
    cart_delete_request,
    fetch_cart_list,
    report_unless_list_success,
)
from k_commerce_cli.commands.cart.interactive import (
    await_unless_cancelled,
    format_deleted_cart_item,
    format_selected_cart_delete_list,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.types import CartItem


async def _run_delete_single(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = common.get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = common.get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    list_result = await fetch_cart_list(terminal, list_provider)
    if list_result is None:
        return "exit"

    while True:
        try:
            selected = await interactive.prompt_cart_item(
                prompts,
                list_result.items,
                selection_prefix="삭제할 상품을 선택하세요",
                allow_back=True,
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if selected == "back":
            return "back"
        if selected == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"
        if not isinstance(selected, CartItem):
            continue

        selected_item = selected
        terminal.echo(format_selected_cart_delete_list((selected_item,)))
        terminal.echo("")
        try:
            confirm = await interactive.prompt_bulk_delete_confirmation(prompts)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if confirm == "back":
            continue
        if confirm == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        delete_result = await await_unless_cancelled(
            terminal,
            delete_provider.delete_cart_item(cart_delete_request(selected_item)),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not delete_result.success:
            terminal.error(delete_result.message)
            continue

        terminal.success(delete_result.message)
        terminal.echo(format_deleted_cart_item(selected_item))

        try:
            should_continue = await interactive.prompt_cart_continue(
                prompts,
                message="삭제를 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if not should_continue:
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        list_result = await fetch_cart_list(terminal, list_provider)
        if list_result is None:
            return "exit"


async def _run_delete_selected(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = common.get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = common.get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    list_result = await fetch_cart_list(terminal, list_provider)
    if list_result is None:
        return "exit"

    while True:
        try:
            selection = await interactive.prompt_cart_items(
                prompts,
                list_result.items,
                selection_prefix="삭제할 상품을 선택하세요",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if selection == "back":
            return "back"
        if selection == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        selected_items = selection
        terminal.echo(format_selected_cart_delete_list(selected_items))
        terminal.echo("")
        try:
            confirm = await interactive.prompt_bulk_delete_confirmation(prompts)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if confirm == "back":
            continue
        if confirm == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        requests = tuple(cart_delete_request(item) for item in selected_items)
        delete_result = await await_unless_cancelled(
            terminal,
            delete_provider.delete_cart_items(requests),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not delete_result.success:
            terminal.error(delete_result.message)
            continue

        terminal.success(delete_result.message)
        for item in selected_items:
            terminal.echo(format_deleted_cart_item(item))

        try:
            should_continue = await interactive.prompt_cart_continue(
                prompts,
                message="삭제를 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if not should_continue:
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        list_result = await fetch_cart_list(terminal, list_provider)
        if list_result is None:
            return "exit"


async def _run_delete_all(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = common.get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = common.get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    while True:
        try:
            action = await interactive.prompt_clear_cart_action(prompts)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if action == "back":
            return "back"
        if action == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"
        if action == "list":
            terminal.info(MSG_LIST_CART)
            list_result = await await_unless_cancelled(
                terminal,
                list_provider.list_cart(),
                message=MSG_INTERACTIVE_CANCELLED,
            )
            if not report_unless_list_success(terminal, list_result):
                return "exit"
            if not list_result.items:
                terminal.echo(MSG_NO_CART_ITEMS)
            else:
                terminal.echo(list_result.message)
            continue

        delete_result = await await_unless_cancelled(
            terminal,
            delete_provider.clear_cart(),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not delete_result.success:
            terminal.error(delete_result.message)
            continue

        terminal.success(delete_result.message)
        terminal.echo(MSG_DELETE_EXITED)
        return "exit"


async def run_delete(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    while True:
        try:
            mode = await interactive.prompt_delete_mode(prompts)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return

        if mode == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return
        if mode == "single":
            outcome = await _run_delete_single(provider, root_dir, terminal, prompts)
            if outcome != "back":
                return
            continue
        if mode == "selected":
            outcome = await _run_delete_selected(provider, root_dir, terminal, prompts)
            if outcome != "back":
                return
            continue

        outcome = await _run_delete_all(provider, root_dir, terminal, prompts)
        if outcome != "back":
            return
