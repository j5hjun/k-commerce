from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.providers.coupang.search.service import (
    CoupangSearchService,
    _SearchBrowserResult,
    _SearchResultItemData,
)
from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.registry import get_provider, list_providers
from k_commerce_cli.services.store import ProviderStore


class _BrowserSpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.close = AsyncMock()
        self.select = AsyncMock(return_value=None)


class _SearchTab:
    def __init__(self, payloads: list[object]) -> None:
        self._payloads = list(payloads)
        self.evaluate_calls: list[str] = []
        self.get_calls: list[str] = []

    async def evaluate(self, script: str):
        self.evaluate_calls.append(script)
        if not self._payloads:
            return []
        return self._payloads.pop(0)

    async def get(self, url: str) -> None:
        self.get_calls.append(url)


class _Session:
    def __init__(self, tab: _SearchTab) -> None:
        self.tab = tab


def _make_search_service(*, root_dir: Path | None = None, browser: _BrowserSpy | None = None) -> CoupangSearchService:
    resolved_root = root_dir if root_dir is not None else Path.home() / ".k-commerce"
    return CoupangSearchService(
        provider_name="coupang",
        store=ProviderStore(ProviderPaths("coupang", root_dir=resolved_root)),
        browser=browser or _BrowserSpy(),
    )


def _build_result() -> _SearchBrowserResult:
    return _SearchBrowserResult(
        state="success",
        items=(
            _SearchResultItemData(
                product_id="8825977723",
                product_name="포스트 아몬드후레이크",
                price="12300",
                rating="4.8",
                image_url="https://example.com/image.jpg",
                product_link="https://www.coupang.com/vp/products/8825977723",
            ),
        ),
    )


def test_get_provider_returns_coupang_provider_instance() -> None:
    provider = get_provider("coupang")

    assert isinstance(provider, CoupangProvider)


def test_get_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported provider: unknown. Supported providers: coupang",
    ):
        get_provider("unknown")


def test_list_providers_includes_builtin_coupang_provider() -> None:
    assert list_providers() == ["coupang"]


@pytest.mark.anyio
async def test_search_products_fails_when_session_is_missing(tmp_path: Path) -> None:
    service = _make_search_service(root_dir=tmp_path)

    result = await service.search_products("후레이크")

    assert result.success is False
    assert result.items == ()
    assert "쿠팡 로그인 상태" in result.message


@pytest.mark.anyio
async def test_scrapes_top_ranked_items_from_rank_markers() -> None:
    service = _make_search_service()
    tab = _SearchTab(
        payloads=[
            {
                "foundRankMarkers": True,
                "items": [
                    {
                        "product_id": "8825977723",
                        "product_name": "포스트 아몬드후레이크",
                        "price": "12300",
                        "rating": "4.8",
                        "image_url": "https://example.com/image.jpg",
                        "product_link": "https://www.coupang.com/vp/products/8825977723",
                    }
                ],
            }
        ]
    )

    items, found_rank_markers = await service._scrape_search_results(tab, max_results=1)

    assert found_rank_markers is True
    assert len(items) == 1
    assert items[0].product_id == "8825977723"
    assert tab.evaluate_calls
    assert "document.querySelector('#product-list')" in tab.evaluate_calls[0]
    assert "const productRoot = productList || document" in tab.evaluate_calls[0]
    assert "productRoot.querySelectorAll('[class*=\"RankMark_rank\"]')" in tab.evaluate_calls[0]
    assert "productRoot.querySelectorAll('a[href*=\"/vp/products/\"]')" in tab.evaluate_calls[0]
    assert "productLink.match(/\\/vp\\/products\\/(\\d+)/)" in tab.evaluate_calls[0]
    assert "itemId" not in tab.evaluate_calls[0]
    assert "closest('li')" in tab.evaluate_calls[0]
    assert "truncateText" in tab.evaluate_calls[0]
    assert "custom-oos" in tab.evaluate_calls[0]
    assert "fw-font-bold" in tab.evaluate_calls[0]
    assert "Math.min(...prices)" in tab.evaluate_calls[0]
    assert "excludeMemberOnly" in tab.evaluate_calls[0]
    assert "parseDiscountRates" in tab.evaluate_calls[0]
    assert "calculatedDiscountCandidates" in tab.evaluate_calls[0]
    assert "basePrice" in tab.evaluate_calls[0]
    assert "\\uC640\\uC6B0" in tab.evaluate_calls[0]
    assert "\\uD68C\\uC6D0" in tab.evaluate_calls[0]
    assert "\\uCFE0\\uD3F0" in tab.evaluate_calls[0]
    assert "fw-gap-y-" in tab.evaluate_calls[0]


@pytest.mark.anyio
async def test_scrape_search_results_fails_when_rank_markers_are_missing() -> None:
    service = _make_search_service()
    tab = _SearchTab(payloads=[{"foundRankMarkers": False, "items": []}])

    items, found_rank_markers = await service._scrape_search_results(tab, max_results=10)

    assert found_rank_markers is False
    assert items == ()


@pytest.mark.anyio
async def test_apply_product_detail_prices_uses_product_page_price() -> None:
    service = _make_search_service()
    tab = _SearchTab(payloads=["9900"])
    session = _Session(tab)
    item = _SearchResultItemData(
        product_id="8825977723",
        product_name="포스트 아몬드후레이크",
        price="12300",
        rating="4.8",
        image_url="https://example.com/image.jpg",
        product_link="https://www.coupang.com/vp/products/8825977723?itemId=1",
    )

    items = await service._apply_product_detail_prices(session, (item,))

    assert tab.get_calls == ["https://www.coupang.com/vp/products/8825977723"]
    assert items[0].price == "9900"
    assert "readTwcRegularSalePrice" in tab.evaluate_calls[0]
    assert "twc-font-bold" in tab.evaluate_calls[0]
    assert "\\uC77C\\uBC18\\uD560\\uC778\\uAC00" in tab.evaluate_calls[0]
    assert "prices.length >= 2 ? Math.min(...prices) : prices[0]" in tab.evaluate_calls[0]
    assert "parseDiscountRates" in tab.evaluate_calls[0]
    assert "total-price" in tab.evaluate_calls[0]
    assert "\\uCFE0\\uD3F0" in tab.evaluate_calls[0]


@pytest.mark.anyio
async def test_search_products_succeeds_with_saved_session(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    browser.launch.return_value = object()
    service = _make_search_service(root_dir=tmp_path, browser=browser)
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")
    service._list_search_results = AsyncMock(return_value=_build_result())

    result = await service.search_products("후레이크")

    assert result.success is True
    assert len(result.items) == 1
    assert result.items[0].product_id == "8825977723"
    assert "검색 결과" in result.message
    browser.launch.assert_awaited_once()
    service._list_search_results.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_to_search_result_formats_table() -> None:
    service = _make_search_service()
    result = service._to_search_result(_build_result())

    assert result.success is True
    assert result.items[0].index == 1
    assert "검색 결과" in result.message

