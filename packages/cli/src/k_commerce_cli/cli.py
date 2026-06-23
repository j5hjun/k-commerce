from __future__ import annotations

import asyncclick as click

from k_commerce_cli.services.login import login as run_login

@click.group(help="CLI for K-Commerce workflows.")
async def app() -> None:
    pass


@app.command()
@click.argument("provider")
async def login(provider: str) -> None:
    try:
        result = await run_login(provider)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    click.echo(result.message)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
