from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.commands.options import provider_argument_with_root_dir_option
from k_commerce_cli.commands.terminal import ClickTerminal
from k_commerce_cli.providers.registry import get_provider


@click.command()
@provider_argument_with_root_dir_option
async def logout(provider: str, root_dir: Path | None) -> None:
    terminal = ClickTerminal()
    try:
        result = await get_provider(provider).logout(root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)

    if not result.success:
        raise click.ClickException(result.message)
