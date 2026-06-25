from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.auth import login as run_login
from k_commerce_cli.services.auth import logout as run_logout
from k_commerce_cli.services.auth import status as run_status


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


@click.group(help="CLI for K-Commerce workflows.")
async def app() -> None:
    pass


def root_dir_option(func):
    return click.option(
        "--root-dir",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help="Override the provider storage root directory.",
    )(func)


@app.group(cls=DefaultCommandGroup, default_command="run")
async def login() -> None:
    pass


@login.command(name="run", hidden=True)
@click.argument("provider")
@root_dir_option
async def login_run(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_login(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


@login.command(name="status")
@click.argument("provider")
@root_dir_option
async def login_status(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_status(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


@app.command()
@click.argument("provider")
@root_dir_option
async def logout(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_logout(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
