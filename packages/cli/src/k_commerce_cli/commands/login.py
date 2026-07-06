from __future__ import annotations

from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.commands.tool_runner import run_tool_command, should_use_generic_runner
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import ToolRuntimeOptions


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.command()
@click.argument("provider", required=False)
@click.option("--request-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read the canonical JSON request from a file.")
@click.option("--root-dir", "--root_dir", type=click.Path(file_okay=False, dir_okay=True), default=None, help="Override the provider root directory.")
@click.pass_context
async def login(ctx: click.Context, provider: str | None, request_file: Path | None, root_dir: str | None) -> None:
    if should_use_generic_runner(provider, request_file):
        await run_tool_command("login", provider, request_file)
        return
    if provider is None:
        raise click.UsageError("Missing argument 'PROVIDER'.")

    terminal = ctx.obj["terminal"]
    try:
        await invoke_tool(
            "login",
            {"provider": provider},
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="provider") from exc
