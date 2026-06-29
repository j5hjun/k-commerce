from __future__ import annotations

import asyncclick as click

from k_commerce_cli.commands.login import login
from k_commerce_cli.commands.logout import logout
from k_commerce_cli.commands.status import status
from k_commerce_cli.terminal.asyncclick import AsyncClickTerminal


@click.group(help="CLI for K-Commerce workflows.")
@click.pass_context
async def app(ctx: click.Context) -> None:
    ctx.ensure_object(dict)
    ctx.obj["terminal"] = AsyncClickTerminal()


app.add_command(login)
app.add_command(status)
app.add_command(logout)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
