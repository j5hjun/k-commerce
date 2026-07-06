from pathlib import Path
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.services.providers.coupang.search.type import (
    SearchProductResult,
    SearchResultItem,
)

RUNNER = CliRunner()


def _search_items() -> tuple[SearchResultItem, ...]:
    return (
        SearchResultItem(
            index=1,
            product_id="8825977723",
            product_name="포스트 아몬드후레이크",
            price="12300",
            rating="4.8",
            image_url="https://example.com/image.jpg",
            product_link="https://www.coupang.com/vp/products/8825977723",
        ),
    )


@pytest.mark.anyio
async def test_search_coupang_command_prints_table_result() -> None:
    search_result = SearchProductResult(
        provider="coupang",
        success=True,
        message="검색 결과 (1개):\n  #  상품ID         가격          리뷰    상품명\n  1  8825977723     12300        4.8     포스트 아몬드후레이크",
        items=_search_items(),
    )
    invoke_tool = AsyncMock(return_value=search_result)

    with (
        patch(
            "k_commerce_cli.commands.search.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch("k_commerce_cli.commands.search.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, ["search", "coupang", "후레이크"])

    assert result.exit_code == 0
    assert "검색 결과" in result.stdout
    invoke_tool.assert_awaited_once()
    assert invoke_tool.await_args.args == (
        "search_products",
        {
            "provider": "coupang",
            "keyword": "후레이크",
            "category": None,
            "sort": "relevance",
            "max_results": 10,
        },
    )
    runtime_options = invoke_tool.await_args.kwargs["runtime_options"]
    assert runtime_options.root_dir is None
    assert runtime_options.terminal is not None


@pytest.mark.anyio
async def test_search_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.search_products = AsyncMock(
        return_value=SearchProductResult(
            provider="coupang",
            success=True,
            message="검색 결과가 없습니다.",
            items=(),
        )
    )

    with patch("k_commerce_cli.commands.search.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(
            app,
            ["search", "coupang", "후레이크", "--root-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.search_products.assert_awaited_once_with(
        "후레이크",
        category=None,
        sort="relevance",
        max_results=10,
    )


@pytest.mark.anyio
async def test_search_coupang_command_outputs_json() -> None:
    provider = Mock()
    provider.search_products = AsyncMock(
        return_value=SearchProductResult(
            provider="coupang",
            success=True,
            message="검색 결과 (1개):",
            items=_search_items(),
        )
    )

    with patch("k_commerce_cli.commands.search.get_provider", return_value=provider):
        result = await RUNNER.invoke(app, ["search", "coupang", "후레이크", "--output", "json"])

    assert result.exit_code == 0
    assert result.stdout.strip().startswith("{")


@pytest.mark.anyio
async def test_search_coupang_command_save_json_file(tmp_path: Path) -> None:
    provider = Mock()
    provider.search_products = AsyncMock(
        return_value=SearchProductResult(
            provider="coupang",
            success=True,
            message="검색 결과 (1개):",
            items=_search_items(),
        )
    )

    save_file = tmp_path / "search.json"
    with patch("k_commerce_cli.commands.search.get_provider", return_value=provider):
        result = await RUNNER.invoke(
            app,
            [
                "search",
                "coupang",
                "후레이크",
                "--output",
                "json",
                "--save",
                str(save_file),
            ],
        )

    assert result.exit_code == 0
    assert save_file.exists()
    assert "product_id" in save_file.read_text(encoding="utf-8")


@pytest.mark.anyio
async def test_search_coupang_command_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.commands.search.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ):
        result = await RUNNER.invoke(app, ["search", "invalid", "후레이크"])

    assert result.exit_code == 2
    assert "Invalid value for provider: Unsupported provider: invalid" in result.output
