from __future__ import annotations

import asyncio
from pathlib import Path

import asyncclick as click

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import prompt_cart_item, prompt_quantity
from k_commerce_cli.prompts import QuestionaryPrompts as Prompts
from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import CartItem, CartQuantityUpdateRequest, ListCartResult

MSG_NO_CART_ITEMS = "장바구니에 담긴 상품이 없습니다."
MSG_INTERACTIVE_CANCELLED = "장바구니 수량 수정을 취소했습니다."
MSG_QUANTITY_UPDATE_CANCELLED = "장바구니 수량 수정을 종료했습니다."


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


def _find_matching_cart_item(
    items: tuple[CartItem, ...],
    selected_item: CartItem,
) -> CartItem | None:
    for item in items:
        if selected_item.vendor_item_id and item.vendor_item_id == selected_item.vendor_item_id:
            return item
        if selected_item.item_id and item.item_id == selected_item.item_id:
            return item
        if selected_item.product_id and item.product_id == selected_item.product_id:
            return item
    return None


def _ensure_list_result(terminal: Terminal, result: ListCartResult) -> None:
    if not result.success:
        terminal.abort(result.message)
    if not result.items:
        terminal.abort(MSG_NO_CART_ITEMS)


def _format_updated_item(item: CartItem) -> str:
    option_text = item.option_text or "-"
    price_text = item.total_price or item.unit_price or "-"
    return f"{item.product_name} / {option_text} / {item.quantity}개 / {price_text}"


async def _run_quantity_update(
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

    async with cart_provider.cart_session() as cart_session:
        list_result = await cart_session.list_cart()
        while True:
            _ensure_list_result(terminal, list_result)

            try:
                selected_item = await prompt_cart_item(
                    prompts,
                    list_result.items,
                    message="수량을 수정할 상품을 선택하세요 (↑↓ 이동, Enter 선택, Ctrl+C 취소):",
                )
                if selected_item is None or not isinstance(selected_item, CartItem):
                    terminal.echo(MSG_QUANTITY_UPDATE_CANCELLED)
                    return
                quantity = await prompt_quantity(prompts, current_quantity=selected_item.quantity)
            except KeyboardInterrupt:
                terminal.abort(MSG_INTERACTIVE_CANCELLED)

            await cart_session.update_cart_quantity(
                CartQuantityUpdateRequest(
                    product_id=selected_item.product_id,
                    vendor_item_id=selected_item.vendor_item_id,
                    item_id=selected_item.item_id,
                    quantity=quantity,
                )
            )

            await asyncio.sleep(1.5)
            list_result = await cart_session.refresh_cart()
            _ensure_list_result(terminal, list_result)
            updated_item = _find_matching_cart_item(list_result.items, selected_item)
            if updated_item is not None:
                terminal.success(_format_updated_item(updated_item))
            if updated_item is not None and updated_item.quantity != quantity:
                terminal.warn(
                    f"요청한 수량은 {quantity}개였지만, 쿠팡 장바구니에는 {updated_item.quantity}개로 반영되었습니다."
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

    try:
        cart_provider = get_provider(
            provider,
            root_dir=resolved_root_dir,
            terminal=ctx.obj["terminal"],
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    result = await cart_provider.list_cart()
    ctx.obj["terminal"].echo(result.message)
