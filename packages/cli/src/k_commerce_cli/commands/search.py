from __future__ import annotations

import json
from pathlib import Path

import asyncclick as click

from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import ToolRequestError, ToolRuntimeOptions

SUPPORTED_SORTS = [
    "relevance",
    "latest",
    "low_price",
    "high_price",
    "review",
]


def _resolve_root_dir(root_dir: str | None) -> Path | None:
    return Path(root_dir) if root_dir is not None else None


@click.command()
@click.argument("provider")
@click.argument("keyword")
@click.option("--category", default=None, help="검색에 사용할 카테고리 ID를 전달합니다.")
@click.option(
    "--sort",
    type=click.Choice(SUPPORTED_SORTS),
    default="relevance",
    show_default=True,
    help="검색 결과 정렬 방식입니다.",
)
@click.option(
    "--output",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="검색 결과 출력 형식입니다.",
)
@click.option(
    "--save",
    type=click.Path(file_okay=False, dir_okay=False),
    default=None,
    help="검색 결과를 JSON 파일로 저장할 경로입니다.",
)
@click.option(
    "--root-dir",
    "--root_dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Override the provider root directory.",
)
@click.pass_context
async def search(
    ctx: click.Context,
    provider: str,
    keyword: str,
    category: str | None,
    sort: str,
    output: str,
    save: str | None,
    root_dir: str | None,
) -> None:
    terminal = ctx.obj["terminal"]
    try:
        result = await invoke_tool(
            "search_products",
            {
                "provider": provider,
                "keyword": keyword,
                "category": category,
                "sort": sort,
                "max_results": 10,
            },
            runtime_options=ToolRuntimeOptions(
                root_dir=_resolve_root_dir(root_dir),
                terminal=terminal,
                get_provider=get_provider,
            ),
        )
    except ValueError as error:
        raise click.BadParameter(str(error), param_hint="provider") from error
    except ToolRequestError as error:
        if error.error_code == "unsupported_provider":
            raise click.BadParameter(error.message, param_hint="provider") from error
        raise

    if not result.success:
        terminal.abort(result.message)

    if output == "json":
        payload = {
            "provider": result.provider,
            "keyword": keyword,
            "category": category,
            "sort": sort,
            "items": [
                {
                    "index": item.index,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "price": item.price,
                    "rating": item.rating,
                    "image_url": item.image_url,
                    "product_link": item.product_link,
                }
                for item in result.items
            ],
        }
        terminal.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        terminal.echo(result.message)

    if save is not None:
        payload = {
            "provider": result.provider,
            "keyword": keyword,
            "category": category,
            "sort": sort,
            "items": [
                {
                    "index": item.index,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "price": item.price,
                    "rating": item.rating,
                    "image_url": item.image_url,
                    "product_link": item.product_link,
                }
                for item in result.items
            ],
        }
        save_path = Path(save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        terminal.info(f"검색 결과를 {save_path}에 저장했습니다.")
