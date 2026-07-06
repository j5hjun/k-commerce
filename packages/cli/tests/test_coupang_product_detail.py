from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.providers.coupang.product.service import CoupangProductService
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import ProductDetailImage, ProductDetailRequest, ProductOcrResult, ProviderName


class _BrowserSpy:
    def __init__(self, session: "_Session | None" = None) -> None:
        self.launch = AsyncMock(return_value=session)
        self.close = AsyncMock()


class _ProductTab:
    def __init__(self, payload) -> None:
        self.payloads = list(payload) if isinstance(payload, list) else [payload]
        self.get_calls: list[str] = []
        self.evaluate_calls: list[str] = []

    async def get(self, url: str) -> None:
        self.get_calls.append(url)

    async def evaluate(self, script: str):
        self.evaluate_calls.append(script)
        if len(self.payloads) == 1:
            return self.payloads[0]
        return self.payloads.pop(0)


class _ClosingProductTab(_ProductTab):
    async def get(self, url: str) -> None:
        self.get_calls.append(url)
        raise RuntimeError("Session with given id not found.")


class _ConnectionClosingProductTab(_ProductTab):
    async def get(self, url: str) -> None:
        self.get_calls.append(url)
        raise ConnectionError("Connection closed")


class _Session:
    def __init__(self, tab: _ProductTab) -> None:
        self.tab = tab


def _make_service(tmp_path: Path, browser: _BrowserSpy) -> CoupangProductService:
    return CoupangProductService(
        provider=ProviderName.COUPANG,
        store=ProviderStore(ProviderPaths("coupang", root_dir=tmp_path)),
        browser=browser,
    )


def _write_session(service: CoupangProductService) -> None:
    service.store.cookies_file.parent.mkdir(parents=True, exist_ok=True)
    service.store.cookies_file.write_text("cookies", encoding="utf-8")


def test_coupang_provider_builds_product_service_like_other_services(tmp_path: Path) -> None:
    # Given: a provider with the same store/browser dependencies used by other services.
    browser = _BrowserSpy()
    provider = CoupangProvider(
        provider=ProviderName.COUPANG,
        store=ProviderStore(ProviderPaths("coupang", root_dir=tmp_path)),
        browser=browser,
    )

    # When: product service is resolved from the provider.
    service = provider.product_service

    # Then: the cached service is built from product_service_cls.
    assert isinstance(service, CoupangProductService)
    assert service is provider.product_service


@pytest.mark.anyio
async def test_product_detail_fails_when_url_is_not_coupang_product(tmp_path: Path) -> None:
    service = _make_service(tmp_path, _BrowserSpy())

    result = await service.get_product_detail(ProductDetailRequest(url="https://example.test/not-product"))

    assert result.success is False
    assert result.error_code == "invalid_url"
    assert result.retryable is False
    assert result.next_tools == ()


@pytest.mark.anyio
async def test_product_detail_fails_when_session_is_missing(tmp_path: Path) -> None:
    service = _make_service(tmp_path, _BrowserSpy())

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is False
    assert result.error_code == "not_logged_in"
    assert result.next_tools == ("login",)


@pytest.mark.anyio
async def test_product_detail_returns_browser_closed_when_tab_closes(tmp_path: Path) -> None:
    tab = _ClosingProductTab(payload={})
    browser = _BrowserSpy(_Session(tab))
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is False
    assert result.message == "브라우저가 닫혀 상품 상세 수집을 완료하지 못했습니다."
    assert result.error_code == "browser_closed"
    assert result.retryable is True
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_product_detail_returns_browser_closed_when_connection_closes(tmp_path: Path) -> None:
    tab = _ConnectionClosingProductTab(payload={})
    browser = _BrowserSpy(_Session(tab))
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is False
    assert result.error_code == "browser_closed"
    assert result.retryable is True
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_product_detail_browser_closed_cleanup_does_not_mask_result(tmp_path: Path) -> None:
    tab = _ClosingProductTab(payload={})
    browser = _BrowserSpy(_Session(tab))
    browser.close.side_effect = ConnectionError("Connection closed")
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is False
    assert result.error_code == "browser_closed"
    assert result.retryable is True
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_product_detail_collects_dom_fields_and_ocr_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_images: tuple[ProductDetailImage, ...] | None = None

    async def extract_all_images(
        images: tuple[ProductDetailImage, ...],
    ) -> tuple[tuple[ProductDetailImage, ...], ProductOcrResult]:
        nonlocal captured_images
        captured_images = images
        return (
            tuple(
                ProductDetailImage(
                    url=image.url,
                    ocr_status="completed",
                )
                for image in images
            ),
            ProductOcrResult(
                enabled=True,
                status="completed",
                model="test",
                scope="full",
                text="OCR 상세 본문",
            ),
        )

    monkeypatch.setattr(
        "k_commerce_cli.services.providers.coupang.product.service.extract_product_image_text",
        extract_all_images,
    )
    tab = _ProductTab(
        {
            "state": "success",
            "productId": "8825977723",
            "itemId": "123",
            "vendorItemId": "456",
            "canonicalUrl": "https://www.coupang.com/vp/products/8825977723",
            "name": "고강도 케이블타이",
            "brand": "OON",
            "description": "튼튼한 케이블타이",
            "price": "12900",
            "currency": "KRW",
            "availability": "InStock",
            "ratingValue": "4.8",
            "ratingCount": "100",
            "breadcrumbs": ["생활용품", "전선정리"],
            "mainImageUrl": "https://example.test/main.jpg",
            "requiredInfo": [{"label": "품명", "value": "케이블타이"}],
            "detailImages": [
                "https://thumbnail.coupangcdn.com/detail-1.jpg",
                "https://thumbnail.coupangcdn.com/detail-2.jpg",
            ],
            "sections": [{"title": "고강도 케이블타이", "text": ""}],
            "tables": [{"title": "제품정보", "headers": ["구분", "길이"], "rows": [["소형", "12CM"]]}],
        }
    )
    browser = _BrowserSpy(_Session(tab))
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(
        ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723?itemId=123&vendorItemId=456")
    )

    assert result.success is True
    assert result.product is not None
    assert result.product.name == "고강도 케이블타이"
    assert result.product.item_id == "123"
    assert result.required_info[0].label == "품명"
    assert captured_images == (
        ProductDetailImage(url="https://thumbnail.coupangcdn.com/detail-1.jpg"),
        ProductDetailImage(url="https://thumbnail.coupangcdn.com/detail-2.jpg"),
    )
    assert result.detail_images[0].ocr_status == "completed"
    assert result.detail_images[1].ocr_status == "completed"
    assert result.ocr.text == "OCR 상세 본문"
    assert result.ocr.scope == "full"
    assert result.tables[0].rows[0].cells == ("소형", "12CM")
    assert tab.get_calls == [
        "https://www.coupang.com/",
        "https://www.coupang.com/vp/products/8825977723?itemId=123&vendorItemId=456",
    ]
    assert "상품정보 더보기" in tab.evaluate_calls[0]
    browser.close.assert_awaited_once()


@pytest.mark.anyio
async def test_product_detail_waits_until_session_product_page_is_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def skip_ocr(
        images: tuple[ProductDetailImage, ...],
    ) -> tuple[tuple[ProductDetailImage, ...], ProductOcrResult]:
        return images, ProductOcrResult(enabled=True, status="no_images", model="", scope="full")

    monkeypatch.setattr(
        "k_commerce_cli.services.providers.coupang.product.service.extract_product_image_text",
        skip_ocr,
    )
    tab = _ProductTab(
        [
            {
                "state": "success",
                "productId": "8825977723",
                "name": "",
            },
            {
                "state": "success",
                "productId": "8825977723",
                "name": "고강도 케이블타이",
                "requiredInfo": [{"label": "품명", "value": "케이블타이"}],
            },
        ]
    )
    browser = _BrowserSpy(_Session(tab))
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is True
    assert result.product is not None
    assert result.product.name == "고강도 케이블타이"
    assert tab.get_calls == [
        "https://www.coupang.com/",
        "https://www.coupang.com/vp/products/8825977723",
    ]
    assert len(tab.evaluate_calls) == 2


@pytest.mark.anyio
async def test_product_detail_waits_for_lazy_detail_images_before_ocr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_images: tuple[ProductDetailImage, ...] | None = None

    async def skip_ocr(
        images: tuple[ProductDetailImage, ...],
    ) -> tuple[tuple[ProductDetailImage, ...], ProductOcrResult]:
        nonlocal captured_images
        captured_images = images
        return images, ProductOcrResult(enabled=True, status="completed", model="test", scope="full", text="상세 OCR")

    monkeypatch.setattr(
        "k_commerce_cli.services.providers.coupang.product.service.extract_product_image_text",
        skip_ocr,
    )
    monkeypatch.setattr(
        "k_commerce_cli.services.providers.coupang.product.service.PRODUCT_PAGE_READY_POLL_SECONDS",
        0.0,
    )
    tab = _ProductTab(
        [
            {
                "state": "success",
                "productId": "8825977723",
                "name": "고강도 케이블타이",
                "requiredInfo": [],
                "detailImages": [],
                "sections": [],
                "tables": [],
            },
            {
                "state": "success",
                "productId": "8825977723",
                "name": "고강도 케이블타이",
                "requiredInfo": [{"label": "품명", "value": "케이블타이"}],
                "detailImages": ["https://thumbnail.coupangcdn.com/detail-1.jpg"],
                "sections": [],
                "tables": [],
            },
        ]
    )
    browser = _BrowserSpy(_Session(tab))
    service = _make_service(tmp_path, browser)
    _write_session(service)

    result = await service.get_product_detail(ProductDetailRequest(url="https://www.coupang.com/vp/products/8825977723"))

    assert result.success is True
    assert result.required_info[0].label == "품명"
    assert captured_images == (ProductDetailImage(url="https://thumbnail.coupangcdn.com/detail-1.jpg"),)
    assert result.detail_images == (ProductDetailImage(url="https://thumbnail.coupangcdn.com/detail-1.jpg"),)
    assert len(tab.evaluate_calls) >= 2
