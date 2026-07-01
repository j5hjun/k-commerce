from pathlib import Path
from typing import Literal

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import (
    await_unless_cancelled,
    format_deleted_cart_item,
    format_selected_cart_delete_list,
    prompt_bulk_delete_confirmation,
    prompt_cart_continue,
    prompt_cart_item,
    prompt_cart_items,
    prompt_clear_cart_action,
    prompt_delete_mode,
    prompt_quantity,
    run_cart_list_browse,
)
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartItem,
    CartQuantityUpdateRequest,
    ListCartResult,
)

MSG_NO_CART_ITEMS = "장바구니에 담긴 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "장바구니 작업을 취소했습니다."
MSG_QUANTITY_UPDATE_EXITED = "장바구니 수량 수정을 종료했습니다."
MSG_DELETE_EXITED = "장바구니 삭제를 종료했습니다."
MSG_LIST_CART = "쿠팡 장바구니 목록을 조회합니다..."
MSG_LIST_BROWSE_EXITED = "장바구니 목록 보기를 종료했습니다."
MSG_EXCLUSIVE_FLAGS = "--list, --quantity, --delete는 함께 사용할 수 없습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def _format_quantity_update_summary(item: CartItem, quantity: int) -> str:
    option_text = item.option_text or "-"
    return f"{item.product_name} / {option_text} / {quantity}개"


def _report_unless_list_success(terminal: Terminal, result: ListCartResult) -> bool:
    if result.success:
        return True
    terminal.error(result.message)
    return False


def _cart_delete_request(item: CartItem) -> CartDeleteRequest:
    return CartDeleteRequest(
        product_id=item.product_id,
        vendor_item_id=item.vendor_item_id,
        item_id=item.item_id,
    )


def _ensure_exclusive_cart_mode(
    *,
    list_only: bool,
    quantity_mode: bool,
    delete_mode: bool,
) -> None:
    if sum([list_only, quantity_mode, delete_mode]) > 1:
        raise click.UsageError(MSG_EXCLUSIVE_FLAGS)


async def _fetch_cart_list(
    terminal: Terminal,
    list_provider,
) -> ListCartResult | None:
    terminal.info(MSG_LIST_CART)
    list_result = await await_unless_cancelled(
        terminal,
        list_provider.list_cart(),
        message=MSG_INTERACTIVE_CANCELLED,
    )
    if not _report_unless_list_success(terminal, list_result):
        return
    if not list_result.items:
        terminal.echo(MSG_NO_CART_ITEMS)
        return None
    return list_result


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
    if not _report_unless_list_success(terminal, list_result):
        return
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
        if not _report_unless_list_success(terminal, list_result):
            return
        if not list_result.items:
            terminal.echo(MSG_NO_CART_ITEMS)
            return


async def _run_delete_single(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    list_result = await _fetch_cart_list(terminal, list_provider)
    if list_result is None:
        return "exit"

    while True:
        try:
            selected = await prompt_cart_item(
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
            confirm = await prompt_bulk_delete_confirmation(prompts)
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
            delete_provider.delete_cart_item(_cart_delete_request(selected_item)),
            message=MSG_INTERACTIVE_CANCELLED,
        )
        if not delete_result.success:
            terminal.error(delete_result.message)
            continue

        terminal.success(delete_result.message)
        terminal.echo(format_deleted_cart_item(selected_item))

        try:
            should_continue = await prompt_cart_continue(
                prompts,
                message="삭제를 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if not should_continue:
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        list_result = await _fetch_cart_list(terminal, list_provider)
        if list_result is None:
            return "exit"


async def _run_delete_selected(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    list_result = await _fetch_cart_list(terminal, list_provider)
    if list_result is None:
        return "exit"

    while True:
        try:
            selection = await prompt_cart_items(
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
            confirm = await prompt_bulk_delete_confirmation(prompts)
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if confirm == "back":
            continue
        if confirm == "exit":
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        requests = tuple(_cart_delete_request(item) for item in selected_items)
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
            should_continue = await prompt_cart_continue(
                prompts,
                message="삭제를 계속하시겠습니까?",
            )
        except KeyboardInterrupt:
            terminal.echo(MSG_INTERACTIVE_CANCELLED)
            return "exit"
        if not should_continue:
            terminal.echo(MSG_DELETE_EXITED)
            return "exit"

        list_result = await _fetch_cart_list(terminal, list_provider)
        if list_result is None:
            return "exit"


async def _run_delete_all(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> Literal["back", "exit"]:
    try:
        delete_provider = get_provider(provider, root_dir=root_dir, terminal=None)
        list_provider = get_provider(provider, root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    while True:
        try:
            action = await prompt_clear_cart_action(prompts)
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
            if not _report_unless_list_success(terminal, list_result):
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


async def _run_delete(
    provider: str,
    root_dir: Path | None,
    terminal: Terminal,
    prompts: Prompts,
) -> None:
    while True:
        try:
            mode = await prompt_delete_mode(prompts)
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
    if not _report_unless_list_success(terminal, result):
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


@click.command("cart")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List cart products only.")
@click.option("--quantity", "quantity_mode", is_flag=True, help="Update a cart product quantity.")
@click.option("--delete", "delete_mode", is_flag=True, help="Delete cart products interactively.")
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
    delete_mode: bool,
    root_dir: str | None,
) -> None:
    resolved_root_dir = _resolve_root_dir(root_dir)
    _ensure_exclusive_cart_mode(
        list_only=list_only,
        quantity_mode=quantity_mode,
        delete_mode=delete_mode,
    )

    if quantity_mode:
        await _run_quantity_update(
            provider,
            resolved_root_dir,
            ctx.obj["terminal"],
            ctx.obj["prompts"],
        )
        return

    if delete_mode:
        await _run_delete(
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
