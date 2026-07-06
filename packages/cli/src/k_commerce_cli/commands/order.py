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
@click.option("--start-date", default=None, help="Filter saved orders from YYYY-MM-DD.")
@click.option("--end-date", default=None, help="Filter saved orders through YYYY-MM-DD.")
@click.option("--status", default="all", help="Filter saved orders by provider status.")
@click.option("--limit", default=50, type=int, help="Maximum saved orders to return.")
@click.option("--cursor", default=None, help="Pagination cursor from a previous order list result.")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_list(
    ctx: click.Context,
    provider: str,
    start_date: str | None,
    end_date: str | None,
    status: str,
    limit: int,
    cursor: str | None,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_list",
            {
                "provider": provider,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "limit": limit,
                "cursor": cursor,
            },
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc


@order.command("sync")
@click.argument("provider")
@click.option("--start-date", default=None, help="Collect orders from YYYY-MM-DD when supported.")
@click.option("--end-date", default=None, help="Collect orders through YYYY-MM-DD when supported.")
@click.option("--refresh", is_flag=True, default=False, help="Rebuild the local order snapshot.")
@click.option(
    "--failed-only",
    is_flag=True,
    default=False,
    help="Retry pages recorded as failed in the local order snapshot.",
)
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_sync(
    ctx: click.Context,
    provider: str,
    start_date: str | None,
    end_date: str | None,
    refresh: bool,
    failed_only: bool,
    root_dir: str | None,
) -> None:
    if refresh and failed_only:
        raise click.UsageError("--refresh and --failed-only cannot be used together.")

    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_sync",
            {
                "provider": provider,
                "start_date": start_date,
                "end_date": end_date,
                "refresh": refresh,
                "failed_only": failed_only,
            },
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc


@order.command("search")
@click.argument("provider")
@click.argument("keyword")
@click.option("--start-date", default=None, help="Search orders from YYYY-MM-DD.")
@click.option("--end-date", default=None, help="Search orders through YYYY-MM-DD.")
@click.option("--limit", default=50, type=int, help="Maximum matched orders to return.")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_search(
    ctx: click.Context,
    provider: str,
    keyword: str,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_search",
            {"provider": provider, "keyword": keyword, "start_date": start_date, "end_date": end_date, "limit": limit},
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc


@order.command("detail")
@click.argument("provider")
@click.argument("order_id")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_detail(
    ctx: click.Context,
    provider: str,
    order_id: str,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_detail",
            {"provider": provider, "order_id": order_id},
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc


@order.command("failures")
@click.argument("provider")
@click.option("--start-date", default=None, help="Filter saved orders from YYYY-MM-DD.")
@click.option("--end-date", default=None, help="Filter saved orders through YYYY-MM-DD.")
@click.option("--limit", default=50, type=int, help="Maximum saved failure orders to return.")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def order_failures(
    ctx: click.Context,
    provider: str,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "order_failures",
            {"provider": provider, "start_date": start_date, "end_date": end_date, "limit": limit},
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc
