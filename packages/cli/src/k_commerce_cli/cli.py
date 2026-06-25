from __future__ import annotations

import asyncclick as click

from k_commerce_cli.commands.login import login
from k_commerce_cli.commands.logout import logout


@click.group(help="CLI for K-Commerce workflows.")
async def app() -> None:
    pass


app.add_command(login)
app.add_command(logout)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")