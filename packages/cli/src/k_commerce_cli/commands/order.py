from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.group()
async def order() -> None:
    pass


@order.command("list")
@click.argument("provider")
@click.option("--refresh", is_flag=True, default=False, help="Rebuild the local order snapshot.")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_list(ctx: click.Context, provider: str, refresh: bool, root_dir: str | None) -> None:
    terminal = ctx.obj["terminal"]
    try:
        provider_service = get_provider(
            provider,
            root_dir=_resolve_root_dir(root_dir),
            terminal=terminal,
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc

    await provider_service.list_orders(refresh=refresh)
