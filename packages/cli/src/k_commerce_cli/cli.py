from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.login import login as run_login


@click.group(help="CLI for K-Commerce workflows.")
async def app() -> None:
    pass


@app.command()
@click.argument("provider")
@click.option(
    "--root-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider storage root directory.",
)
async def login(provider: str, root_dir: Path | None) -> None:
    try:
        result = await run_login(provider, root_dir=root_dir)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
