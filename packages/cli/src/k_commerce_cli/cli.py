from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.login import login as run_login
from k_commerce_cli.services.login_status import login_status as run_login_status
from k_commerce_cli.services.logout import logout as run_logout


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


def provider_command(func):
    return app.command()(click.argument("provider")(root_dir_option(func)))


async def echo_login(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_login(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


@app.group()
async def login() -> None:
    pass


@login.command()
@root_dir_option
async def coupang(root_dir: Path | None) -> None:
    await echo_login("coupang", root_dir)


@login.command()
@click.argument("provider")
@root_dir_option
async def status(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_login_status(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


@provider_command
async def logout(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_logout(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
