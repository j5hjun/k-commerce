from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

import asyncclick as click

F = TypeVar("F", bound=Callable[..., object])


def provider_argument_with_root_dir_option(func: F) -> F:
    return click.argument("provider")(
        click.option(
            "--root-dir",
            type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
            default=None,
            help="Override the provider storage root directory.",
        )(func)
    )
