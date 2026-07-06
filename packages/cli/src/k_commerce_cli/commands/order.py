from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import ToolRuntimeOptions


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.group()
async def order() -> None:
    pass


@order.command("list")
@click.argument("provider")
@click.option("--refresh", is_flag=True, default=False, help="Rebuild the local order snapshot.")
@click.option(
    "--failed-only",
    is_flag=True,
    default=False,
    help="Retry pages recorded as failed in the local order snapshot.",
)
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_list(
    ctx: click.Context,
    provider: str,
    refresh: bool,
    failed_only: bool,
    root_dir: str | None,
) -> None:
    if refresh and failed_only:
        raise click.UsageError("--refresh and --failed-only cannot be used together.")

    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_list",
            {"provider": provider, "refresh": refresh, "failed_only": failed_only},
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc
