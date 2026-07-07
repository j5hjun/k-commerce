from __future__ import annotations

import json
from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.serialization import to_jsonable
from k_commerce_cli.services.tools.types import ToolRequestError, ToolRuntimeOptions


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.group()
async def product() -> None:
    pass


@product.command("detail")
@click.argument("provider")
@click.argument("url")
@click.option("--root-dir", "--root_dir", default=None, help="Override the provider root directory.")
@click.pass_context
async def product_detail(
    ctx: click.Context,
    provider: str,
    url: str,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        result = await invoke_tool(
            "product_detail",
            {
                "provider": provider,
                "url": url,
            },
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc
    except ToolRequestError as exc:
        if exc.error_code == "unsupported_provider":
            raise click.BadParameter(exc.message, param_hint="provider") from exc
        raise

    terminal.echo(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))
