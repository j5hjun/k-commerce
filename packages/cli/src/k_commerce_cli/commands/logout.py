from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.commands.options import provider_argument_with_root_dir_option
from k_commerce_cli.services.registry import get_provider


@click.command()
@provider_argument_with_root_dir_option
async def logout(ctx: click.Context, provider: str, root_dir: Path | None) -> None:
    terminal = ctx.obj.get("terminal") if ctx.obj is not None else None
    try:
        await get_provider(provider).logout(root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error
