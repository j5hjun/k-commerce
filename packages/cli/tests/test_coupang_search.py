from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock

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
    assert "RankMark_rank" in tab.evaluate_calls[0]
    assert "expectedRanks.every" in tab.evaluate_calls[0]
    assert "productLink.match(/\\/vp\\/products\\/(\\d+)/)" in tab.evaluate_calls[0]
    assert "itemId" not in tab.evaluate_calls[0]
    assert "closest('li[class*=\"ProductUnit_productUnit\"], li')" in tab.evaluate_calls[0]
    assert "truncateText" in tab.evaluate_calls[0]
    assert "custom-oos" in tab.evaluate_calls[0]
    assert "collectPriceEntries" in tab.evaluate_calls[0]
    assert "customOosRoots" in tab.evaluate_calls[0]
    assert "leafWonNodes" in tab.evaluate_calls[0]
    assert "priceRoots = [element]" in tab.evaluate_calls[0]
    assert "\\uC801\\uB9BD" in tab.evaluate_calls[0]
    assert "priceEntries" in tab.evaluate_calls[0]
    assert "highestPrice" in tab.evaluate_calls[0]
    assert "couponNodes" in tab.evaluate_calls[0]
    assert "uniquePriceValues.length === 1" in tab.evaluate_calls[0]
    assert "remainingEntries.length === 1" in tab.evaluate_calls[0]
    assert "nearestIndex" in tab.evaluate_calls[0]
    assert "remainingEntries.length > 1" in tab.evaluate_calls[0]
    assert "\\uCFE0\\uD3F0" in tab.evaluate_calls[0]


@pytest.mark.anyio
async def test_scrape_search_results_returns_only_ranked_dom_items() -> None:
    service = _make_search_service()
    tab = _SearchTab(
        payloads=[
            {
                "foundRankMarkers": False,
                "items": [],
            }
        ]
    )

    items, found_rank_markers = await service._scrape_search_results(tab, max_results=1)

    assert found_rank_markers is False
    assert items == ()
    assert "application/ld+json" not in tab.evaluate_calls[0]


@pytest.mark.anyio
async def test_scrape_search_results_fails_when_rank_markers_are_missing() -> None:
    service = _make_search_service()
    tab = _SearchTab(payloads=[{"foundRankMarkers": False, "items": []}])

    items, found_rank_markers = await service._scrape_search_results(tab, max_results=10)

    assert found_rank_markers is False
    assert items == ()


@pytest.mark.anyio
async def test_scrape_search_results_scrolls_until_all_rank_markers_are_found() -> None:
    service = _make_search_service()
    tab = _SearchTab(
        payloads=[
            {
                "foundRankMarkers": False,
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
            },
            True,
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
                    },
                    {
                        "product_id": "4914224511",
                        "product_name": "켈로그 현미 푸레이크",
                        "price": "8900",
                        "rating": "1234",
                        "image_url": "https://example.com/image2.jpg",
                        "product_link": "https://www.coupang.com/vp/products/4914224511",
                    },
                ],
            },
        ]
    )

    items, found_all_rank_markers = await service._scrape_search_results_with_scroll(tab, max_results=2)

    assert found_all_rank_markers is True
    assert len(items) == 2
    assert "window.scrollBy" in tab.evaluate_calls[1]


@pytest.mark.anyio
async def test_list_search_results_does_not_visit_product_detail_pages() -> None:
    service = _make_search_service()
    tab = _SearchTab(payloads=[])
    session = _Session(tab)
    service._active_tab = Mock(return_value=tab)
    service._is_logged_in = AsyncMock(return_value=True)
    service._wait_for_search_page_ready = AsyncMock()
    service._scrape_search_results_with_scroll = AsyncMock(return_value=(_build_result().items, True))

    result = await service._list_search_results(
        session,
        keyword="우산",
        category=None,
        sort="relevance",
        max_results=10,
    )

    assert result.state == "success"
    assert tab.get_calls == ["https://www.coupang.com/np/search?q=%EC%9A%B0%EC%82%B0&page=1"]
    assert all("/vp/products/" not in url for url in tab.get_calls)


def test_to_search_result_includes_incomplete_rank_warning() -> None:
    service = _make_search_service()
    result = service._to_search_result(
        _SearchBrowserResult(
            state="success",
            items=_build_result().items,
            message="10개 모두 불러오지 못했습니다",
        )
    )

    assert result.success is True
    assert result.message.startswith("10개 모두 불러오지 못했습니다")


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

