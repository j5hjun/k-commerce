from __future__ import annotations

import asyncclick as click

from k_commerce_cli.commands.cart import cart
from k_commerce_cli.commands.login import login
from k_commerce_cli.commands.order import order
from k_commerce_cli.commands.logout import logout
from k_commerce_cli.commands.product import product
from k_commerce_cli.commands.review import review
from k_commerce_cli.commands.search import search
from k_commerce_cli.commands.status import status
from k_commerce_cli.commands.tool_runner import generic_tool_command, is_canonical_tool_name
from k_commerce_cli.terminal.asyncclick import AsyncClickTerminal
from k_commerce_cli.prompts import QuestionaryPrompts


class CommerceGroup(click.Group):
    def get_command(
        self,
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        if is_canonical_tool_name(cmd_name):
            return generic_tool_command(cmd_name)
        return None


@click.group(cls=CommerceGroup, help="CLI for K-Commerce workflows.")
@click.pass_context
async def app(ctx: click.Context) -> None:
    ctx.ensure_object(dict)
    ctx.obj["terminal"] = AsyncClickTerminal()
    ctx.obj["prompts"] = QuestionaryPrompts()


app.add_command(login)
app.add_command(status)
app.add_command(order)
app.add_command(logout)
app.add_command(product)
app.add_command(review)
app.add_command(search)
app.add_command(cart)


def main(argv: list[str] | None = None) -> int:
    return app(args=argv, prog_name="k-commerce")
