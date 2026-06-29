from __future__ import annotations

import asyncclick as click

from k_commerce_cli.commands.review.list import review_list
from k_commerce_cli.commands.review.upload import review_upload


@click.group()
async def review() -> None:
    """Review commands."""


review.add_command(review_upload)
review.add_command(review_list)
