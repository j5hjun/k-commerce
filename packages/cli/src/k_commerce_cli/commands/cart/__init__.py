from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.command("cart")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List cart products only.")
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
    root_dir: str | None,
) -> None:
    try:
        cart_provider = get_provider(
            provider,
            root_dir=_resolve_root_dir(root_dir),
            terminal=ctx.obj["terminal"],
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error

    await cart_provider.list_cart()
