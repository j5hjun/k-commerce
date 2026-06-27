from __future__ import annotations

import re
from pathlib import Path

import asyncclick as click

from k_commerce_cli.commands.login import DefaultCommandGroup
from k_commerce_cli.commands.options import provider_argument_with_root_dir_option
from k_commerce_cli.providers.registry import get_provider
from k_commerce_cli.types import OrderListEntry, OrderListResult


def _normalize_order_field(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).replace("|", " ")).strip()


def _format_order_entry(entry: OrderListEntry) -> str:
    line = (
        f"주문일: {_normalize_order_field(entry.order_date)} | "
        f"상품: {_normalize_order_field(entry.title)} | "
        f"수량: {entry.quantity} | "
        f"상태: {_normalize_order_field(entry.status)}"
    )
    if entry.product_url:
        line += f" | URL: {_normalize_order_field(entry.product_url)}"
    return line


def _render_order_list(result: OrderListResult) -> tuple[str, ...]:
    if not result.orders:
        return ("조회된 주문이 없습니다.",)

    return tuple(_format_order_entry(entry) for entry in result.orders)


@click.group(cls=DefaultCommandGroup, default_command="list")
async def order() -> None:
    """Order commands."""
    pass


@order.command(name="list")
@provider_argument_with_root_dir_option
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Ignore cached orders and fetch a fresh order list.",
)
async def order_list(provider: str, root_dir: Path | None, refresh: bool) -> None:
    try:
        result = await get_provider(provider).order.list(root_dir=root_dir, refresh=refresh)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    if not result.success:
        click.echo(result.message)
        raise click.ClickException(result.message)

    for line in _render_order_list(result):
        click.echo(line)
    click.echo(result.message)
