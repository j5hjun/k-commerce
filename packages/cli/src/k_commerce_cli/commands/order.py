from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.commands.options import provider_argument_with_root_dir_option
from k_commerce_cli.services.registry import get_provider


@click.group()
async def order() -> None:
    """Order commands."""


@order.command(name="list")
@provider_argument_with_root_dir_option
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Ignore previous comparison and recreate orders.json from the latest collection.",
)
async def order_list(
    ctx: click.Context,
    provider: str,
    root_dir: Path | None,
    refresh: bool,
) -> None:
    terminal = ctx.obj.get("terminal") if ctx.obj is not None else None
    try:
        await get_provider(provider).list_orders(
            root_dir=root_dir,
            terminal=terminal,
            refresh=refresh,
        )
    except ValueError as error:
        raise click.BadParameter(str(error)) from error
