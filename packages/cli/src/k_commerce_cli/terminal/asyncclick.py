from __future__ import annotations

import asyncclick as click
from typing import NoReturn

from k_commerce_cli.base import Terminal


class AsyncClickTerminal(Terminal):
    def echo(self, message: str) -> None:
        click.echo(message)

    def info(self, message: str) -> None:
        click.echo(message)

    def success(self, message: str) -> None:
        click.secho(f"[ok] {message}", fg="green")

    def warn(self, message: str) -> None:
        click.secho(f"[warn] {message}", fg="yellow")

    def cache(self, message: str) -> None:
        click.secho(f"[cache] {message}", dim=True)

    def abort(self, message: str) -> NoReturn:
        raise click.ClickException(message)
