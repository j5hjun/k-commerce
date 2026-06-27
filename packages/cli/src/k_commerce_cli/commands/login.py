from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.commands.options import provider_argument_with_root_dir_option
from k_commerce_cli.services.registry import get_provider


class DefaultCommandGroup(click.Group):
    def __init__(self, *args, default_command: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.default_command = default_command

    async def resolve_command(self, ctx: click.Context, args: list[str]):
        if args:
            protected_args = {"--help", "-h"}
            if args[0] not in self.commands and args[0] not in protected_args:
                default = self.get_command(ctx, self.default_command)
                if default is not None:
                    return self.default_command, default, args

        return await super().resolve_command(ctx, args)


@click.group(cls=DefaultCommandGroup, default_command="run")
async def login() -> None:
    """Login commands."""
    pass


@login.command(name="run", hidden=True)
@provider_argument_with_root_dir_option
async def login_run(ctx: click.Context, provider: str, root_dir: Path | None) -> None:
    terminal = ctx.obj.get("terminal") if ctx.obj is not None else None
    try:
        result = await get_provider(provider).login(root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)

    if not result.success:
        raise click.ClickException(result.message)


@login.command(name="status")
@provider_argument_with_root_dir_option
async def login_status(ctx: click.Context, provider: str, root_dir: Path | None) -> None:
    terminal = ctx.obj.get("terminal") if ctx.obj is not None else None
    try:
        result = await get_provider(provider).status(root_dir=root_dir, terminal=terminal)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)
