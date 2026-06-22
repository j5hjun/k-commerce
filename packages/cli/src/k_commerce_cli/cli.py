from __future__ import annotations

import typer

from k_commerce_cli.services.login import login as run_login

app = typer.Typer(help="CLI for K-Commerce workflows.")


@app.callback()
def cli() -> None:
    pass


@app.command()
def login(provider: str) -> None:
    try:
        print(run_login(provider))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
