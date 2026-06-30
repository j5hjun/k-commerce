from __future__ import annotations

import asyncclick as click

from k_commerce_cli.commands.review.delete import review_delete
from k_commerce_cli.commands.review.edit import review_edit
from k_commerce_cli.commands.review.upload import review_upload


@click.group()
async def review() -> None:
    """Review commands."""


review.add_command(review_delete)
review.add_command(review_edit)
review.add_command(review_upload)
