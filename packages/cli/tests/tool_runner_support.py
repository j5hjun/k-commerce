from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.providers.coupang.types import (
    CoupangDeliveryGroup,
    CoupangOrderList,
    CoupangOrderMeta,
    CoupangOrderProduct,
    CoupangOrderResult,
    CoupangOrderSummary,
)
from k_commerce_cli.services.types import (
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    OrderSearchRequest,
    OrderSearchResult,
    ProductDetailRequest,
    ProductDetailResult,
    ProductOcrResult,
    ProviderName,
)
from k_commerce_cli.services.types.auth import LoginResult, LogoutResult, StatusResult


@dataclass(frozen=True, slots=True)
class ProviderCall:
    name: str
    request: CartQuantityUpdateRequest | OrderSearchRequest | ProductDetailRequest | None = None


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[ProviderCall] = []

    async def login(self) -> LoginResult:
        self.calls.append(ProviderCall("login"))
        return LoginResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그인 성공",
        )

    async def status(self) -> StatusResult:
        self.calls.append(ProviderCall("status"))
        return StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )

    async def logout(self) -> LogoutResult:
        self.calls.append(ProviderCall("logout"))
        return LogoutResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그아웃 완료",
        )

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        return CartQuantityUpdateResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 수량 수정 성공",
            quantity=request.quantity,
            product_id=request.product_id,
            vendor_item_id=request.vendor_item_id,
            item_id=request.item_id,
        )

    async def search_orders(self, request: OrderSearchRequest) -> OrderSearchResult:
        self.calls.append(ProviderCall("search_orders", request))
        return OrderSearchResult(
            success=True,
            provider="coupang",
            message="주문 검색 완료: 1건(전체 1건)",
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            total_count=1,
            payload=CoupangOrderList(
                meta=CoupangOrderMeta(
                    provider=ProviderName.COUPANG,
                    collectedAt="2026-07-01T00:00:00+09:00",
                    years=["2026"],
                    failedPages=[],
                    refresh=False,
                    summary=CoupangOrderSummary(
                        totalOrders=1,
                        addedOrders=0,
                        updatedOrders=0,
                        deletedOrders=0,
                    ),
                ),
                orders=[
                    CoupangOrderResult(
                        provider=ProviderName.COUPANG,
                        orderId=1,
                        title="가방걸이",
                        orderedAt=1780272000000,
                        totalProductPrice=1000,
                        deliveryGroupList=[
                            CoupangDeliveryGroup(
                                shipmentBoxId="box-1",
                                invoiceNumber="invoice-1",
                                invoiceStatus="FINAL_DELIVERY",
                                pddMessage={"message": "done"},
                                productList=[
                                    CoupangOrderProduct(
                                        vendorItemId=3,
                                        vendorItemName="가방걸이",
                                        productName="가방걸이",
                                        quantity=1,
                                        unitPrice=1000,
                                        discountedUnitPrice=1000,
                                        combinedUnitPrice=1000,
                                        imagePath="https://example.test/bag-hook.jpg",
                                        productUrl="https://www.coupang.com/vp/products/1?itemId=2&vendorItemId=3",
                                        productId=1,
                                        itemId=2,
                                    )
                                ],
                            )
                        ],
                    )
                ],
            ),
        )

    async def get_product_detail(self, request: ProductDetailRequest) -> ProductDetailResult:
        self.calls.append(ProviderCall("get_product_detail", request))
        return ProductDetailResult(
            success=True,
            provider="coupang",
            message="상품 상세 수집 완료",
            url=request.url,
            product=None,
            required_info=(),
            detail_images=(),
            sections=(),
            tables=(),
            ocr=ProductOcrResult(enabled=True, status="completed", model="test", scope="full", text="OCR 상세 본문"),
        )


@contextmanager
def patched_tool_provider(fake_provider: FakeProvider) -> Generator[None]:
    def get_provider(
        provider: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> FakeProvider:
        assert provider == "coupang"
        assert root_dir is None
        assert terminal is None
        return fake_provider

    with patch("k_commerce_cli.commands.tool_runner.default_get_provider", side_effect=get_provider):
        yield


def write_cart_update_request(tmp_path: Path) -> Path:
    request_file = tmp_path / "cart-update.json"
    _ = request_file.write_text(
        json.dumps(
            {
                "provider": "coupang",
                "product_id": "p",
                "vendor_item_id": "v",
                "item_id": "i",
                "quantity": 3,
            }
        ),
        encoding="utf-8",
    )
    return request_file
