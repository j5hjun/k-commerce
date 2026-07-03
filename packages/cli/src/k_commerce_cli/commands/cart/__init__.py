import asyncclick as click

from k_commerce_cli.commands.cart.common import MSG_EXCLUSIVE_FLAGS, resolve_root_dir
from k_commerce_cli.commands.cart.delete import run_delete
from k_commerce_cli.commands.cart.list import run_cart_list
from k_commerce_cli.commands.cart.quantity import run_quantity_update

__all__ = ["cart"]


def _ensure_exclusive_cart_mode(
    *,
    list_only: bool,
    quantity_mode: bool,
    delete_mode: bool,
) -> None:
    if sum([list_only, quantity_mode, delete_mode]) > 1:
        raise click.UsageError(MSG_EXCLUSIVE_FLAGS)


@click.command("cart")
@click.argument("provider")
@click.option("--list", "list_only", is_flag=True, help="List cart products only.")
@click.option("--quantity", "quantity_mode", is_flag=True, help="Update a cart product quantity.")
@click.option("--delete", "delete_mode", is_flag=True, help="Delete cart products interactively.")
@click.option(
    "--root-dir",
    "--root_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider root directory.",
)
@click.pass_context
async def cart(
    ctx: click.Context,
    provider: str,
    list_only: bool,
    quantity_mode: bool,
    delete_mode: bool,
    root_dir: str | None,
) -> None:
    resolved_root_dir = resolve_root_dir(root_dir)
    _ensure_exclusive_cart_mode(
        list_only=list_only,
        quantity_mode=quantity_mode,
        delete_mode=delete_mode,
    )

    terminal = ctx.obj["terminal"]
    prompts = ctx.obj["prompts"]

    if quantity_mode:
        await run_quantity_update(provider, resolved_root_dir, terminal, prompts)
        return

    if delete_mode:
        await run_delete(provider, resolved_root_dir, terminal, prompts)
        return

    await run_cart_list(provider, resolved_root_dir, terminal, prompts)
