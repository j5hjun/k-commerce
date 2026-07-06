from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.orders import CoupangOrderService
from k_commerce_cli.services.providers.coupang.types import (
    CoupangDeliveryGroup,
    CoupangOrderList,
    CoupangOrderMeta,
    CoupangOrderProduct,
    CoupangOrderResult,
    CoupangOrderSummary,
)
from k_commerce_cli.services.types import OrderSyncRequest, ProviderName


class ExceptionDetails:
    def __init__(self, text: str, description: str) -> None:
        self.text = text
        self.exception = type("RemoteException", (), {"description": description})()


class _StoreStub:
    def __init__(self, root_dir: Path, *, has_session: bool = True):
        self.paths = ProviderPaths("coupang", root_dir)
        self.base_dir = self.paths.base_dir
        self.profile_dir = self.paths.profile_dir
        self.cookies_file = self.paths.cookies_file
        self.credentials_path = self.paths.credentials_path
        self.session_meta_path = self.paths.session_meta_path
        self.orders_path = self.paths.orders_path
        self._orders = None
        self._has_session = has_session

    def load_credentials(self):
        return None

    def has_session(self) -> bool:
        return self._has_session

    def clear_session(self) -> bool:
        return False

    def write_session_metadata(self, payload):
        return None

    def load_orders(self):
        return self._orders

    def write_orders(self, payload):
        self._orders = payload


def _order_payload(
    *,
    order_id: int,
    title: str,
    ordered_at: int = 1767225600000,
    shipment_box_id: str = "A",
    invoice_number: str = "1",
    invoice_status: str = "FINAL_DELIVERY",
    message: str = "done",
    vendor_item_id: int = 101,
    product_id: int = 1001,
    item_id: int = 2001,
    item_name: str = "item",
    price: int = 1000,
) -> dict[str, Any]:
    return {
        "orderId": order_id,
        "title": title,
        "orderedAt": ordered_at,
        "deliveryGroupList": [
            {
                "shipmentBoxId": shipment_box_id,
                "invoiceNumber": invoice_number,
                "invoiceStatus": invoice_status,
                "pddMessage": {"message": message},
                "productList": [
                    {
                        "vendorItemId": vendor_item_id,
                        "productId": product_id,
                        "itemId": item_id,
                        "vendorItemName": item_name,
                        "productName": item_name,
                        "quantity": 1,
                        "unitPrice": price,
                        "discountedUnitPrice": price,
                        "combinedUnitPrice": price,
                        "imagePath": f"https://example.com/{item_name}.jpg",
                    }
                ],
            }
        ],
        "totalProductPrice": price,
    }


def _order_result(**kwargs: Any) -> CoupangOrderResult:
    return CoupangOrderResult.from_dict(
        {
            "provider": "coupang",
            **_order_payload(**kwargs),
        }
    )


@pytest.mark.anyio
async def test_collect_orders_refresh_writes_meta_and_nested_orders(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026", "2025"],
            {
                "orderList": [
                    {
                        "orderId": 10,
                        "title": "first",
                        "orderedAt": 1,
                        "deliveryGroupList": [
                            {
                                "shipmentBoxId": "A",
                                "invoiceNumber": "1",
                                "invoiceStatus": "FINAL_DELIVERY",
                                "pddMessage": {"message": "done"},
                                "productList": [
                                    {
                                        "vendorItemId": 101,
                                        "productId": 1001,
                                        "itemId": 2001,
                                        "vendorItemName": "item",
                                        "productName": "item",
                                        "quantity": 1,
                                        "unitPrice": 1000,
                                        "discountedUnitPrice": 1000,
                                        "combinedUnitPrice": 1000,
                                        "imagePath": "https://example.com/item.jpg",
                                    }
                                ],
                            }
                        ],
                        "totalProductPrice": 1000,
                    }
                ],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
            {
                "orderList": [],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))
    payload = result.payload

    assert payload.meta.provider == "coupang"
    assert payload.meta.years == ["2026", "2025"]
    assert payload.meta.refresh is True
    assert payload.orders[0].provider == "coupang"
    assert payload.orders[0].orderId == 10
    product = payload.orders[0].deliveryGroupList[0].productList[0]
    assert product.productUrl == (
        "https://www.coupang.com/vp/products/1001?itemId=2001&vendorItemId=101"
    )
    tab.get.assert_any_await("https://mc.coupang.com/ssr/desktop/order/list")
    assert store._orders == payload.to_dict()
    assert result.message == "주문 새로 생성 완료: 총 1건"


@pytest.mark.anyio
async def test_list_orders_returns_not_logged_in_when_session_is_missing(
    tmp_path: Path,
) -> None:
    store = _StoreStub(tmp_path, has_session=False)
    browser = Mock()
    browser.launch = AsyncMock()
    browser.close = AsyncMock()
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."
    assert result.payload.orders == []
    assert result.error_code == "not_logged_in"
    assert result.retryable is False
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()
    browser.close.assert_not_awaited()


@pytest.mark.anyio
async def test_list_orders_returns_not_logged_in_when_order_page_redirects_to_login(
    tmp_path: Path,
) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    tab.evaluate = AsyncMock(
        return_value={
            "url": "https://login.coupang.com/login/login.pang",
            "body_text": "로그인이 필요합니다",
            "has_password_input": True,
        }
    )
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."
    assert result.payload.orders == []
    assert result.error_code == "not_logged_in"
    assert result.retryable is False
    assert result.next_tools == ("login",)
    browser.close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_list_orders_returns_browser_closed_when_initial_navigation_closes(
    tmp_path: Path,
) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock(side_effect=RuntimeError("Session with given id not found."))
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.message == "브라우저가 닫혀 주문 수집을 완료하지 못했습니다."
    assert result.payload.orders == []
    assert result.error_code == "browser_closed"
    assert result.retryable is True
    assert result.next_tools == ()
    browser.close.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_collect_orders_diff_counts_orders_not_items(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    store._orders = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="old",
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
                orderId=10,
                title="first",
                orderedAt=1,
                totalProductPrice=1000,
                deliveryGroupList=[
                    CoupangDeliveryGroup(
                        shipmentBoxId="A",
                        invoiceNumber="1",
                        invoiceStatus="INSTRUCT",
                        pddMessage={"message": "old"},
                        productList=[
                            CoupangOrderProduct(
                                vendorItemId=101,
                                vendorItemName="item",
                                productName="item",
                                quantity=1,
                                unitPrice=1000,
                                discountedUnitPrice=1000,
                                combinedUnitPrice=1000,
                                imagePath="https://example.com/item.jpg",
                            )
                        ],
                    )
                ],
            )
        ],
    ).to_dict()
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            {
                "orderList": [
                    {
                        "orderId": 10,
                        "title": "first",
                        "orderedAt": 1,
                        "deliveryGroupList": [
                            {
                                "shipmentBoxId": "A",
                                "invoiceNumber": "1",
                                "invoiceStatus": "FINAL_DELIVERY",
                                "pddMessage": {"message": "done"},
                                "productList": [
                                    {
                                        "vendorItemId": 101,
                                        "vendorItemName": "item",
                                        "productName": "item",
                                        "quantity": 1,
                                        "unitPrice": 1000,
                                        "discountedUnitPrice": 1000,
                                        "combinedUnitPrice": 1000,
                                        "imagePath": "https://example.com/item.jpg",
                                    }
                                ],
                            }
                        ],
                        "totalProductPrice": 1000,
                    }
                ],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=False))
    payload = result.payload

    assert payload.meta.summary == CoupangOrderSummary(
        totalOrders=1,
        addedOrders=0,
        updatedOrders=1,
        deletedOrders=0,
    )
    assert result.message == "주문 수집 완료: 총 1건, 추가 0건, 변경 1건, 삭제 0건"


@pytest.mark.anyio
async def test_collect_orders_reuses_cached_tail_after_unchanged_page(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    store._orders = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="old",
            years=["2026"],
            failedPages=[],
            refresh=False,
            summary=CoupangOrderSummary(
                totalOrders=2,
                addedOrders=0,
                updatedOrders=0,
                deletedOrders=0,
            ),
        ),
        orders=[
            _order_result(order_id=10, title="first"),
            _order_result(
                order_id=20,
                title="second",
                shipment_box_id="B",
                invoice_number="2",
                vendor_item_id=202,
                item_name="item2",
                price=2000,
            ),
        ],
    ).to_dict()
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            {
                "orderList": [_order_payload(order_id=10, title="first")],
                "orderPagination": {"hasNext": True, "nextPageIndex": 1},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=False))

    assert [order.orderId for order in result.payload.orders] == [10, 20]
    assert result.payload.meta.summary == CoupangOrderSummary(
        totalOrders=2,
        addedOrders=0,
        updatedOrders=0,
        deletedOrders=0,
    )
    assert tab.get.await_count == 2
    tab.get.assert_any_await(
        "https://mc.coupang.com/ssr/desktop/order/list?requestYear=2026&pageIndex=0"
    )


@pytest.mark.anyio
async def test_collect_orders_ignores_cache_when_previous_snapshot_has_failures(
    tmp_path: Path,
) -> None:
    store = _StoreStub(tmp_path)
    store._orders = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="old",
            years=["2026"],
            failedPages=[["2026", 2]],
            refresh=False,
            summary=CoupangOrderSummary(
                totalOrders=2,
                addedOrders=0,
                updatedOrders=0,
                deletedOrders=0,
            ),
        ),
        orders=[
            _order_result(order_id=10, title="first"),
            _order_result(
                order_id=20,
                title="second",
                shipment_box_id="B",
                invoice_number="2",
                vendor_item_id=202,
                item_name="item2",
                price=2000,
            ),
        ],
    ).to_dict()
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            {
                "orderList": [_order_payload(order_id=10, title="first")],
                "orderPagination": {"hasNext": True, "nextPageIndex": 1},
            },
            {
                "orderList": [
                    _order_payload(
                        order_id=20,
                        title="second",
                        shipment_box_id="B",
                        invoice_number="2",
                        vendor_item_id=202,
                        item_name="item2",
                        price=2000,
                    )
                ],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=False))

    assert [order.orderId for order in result.payload.orders] == [10, 20]
    assert result.payload.meta.failedPages == []
    tab.get.assert_any_await(
        "https://mc.coupang.com/ssr/desktop/order/list?requestYear=2026&pageIndex=1"
    )


@pytest.mark.anyio
async def test_collect_orders_reports_failed_pages_in_message(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            RuntimeError("boom"),
            RuntimeError("boom"),
            RuntimeError("boom"),
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))
    payload = result.payload

    assert payload.meta.failedPages == [["2026", 1]]
    assert payload.meta.summary == CoupangOrderSummary(
        totalOrders=0,
        addedOrders=0,
        updatedOrders=0,
        deletedOrders=0,
    )
    assert result.message == "주문 새로 생성 완료: 총 0건, 실패 1페이지(2026년 1페이지)"


@pytest.mark.anyio
async def test_collect_orders_failed_only_retries_recorded_pages(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    store._orders = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="old",
            years=["2026"],
            failedPages=[["2026", 2]],
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
                orderId=10,
                title="first",
                orderedAt=1,
                totalProductPrice=1000,
                deliveryGroupList=[
                    CoupangDeliveryGroup(
                        shipmentBoxId="A",
                        invoiceNumber="1",
                        invoiceStatus="FINAL_DELIVERY",
                        pddMessage={"message": "done"},
                        productList=[
                            CoupangOrderProduct(
                                vendorItemId=101,
                                vendorItemName="item",
                                productName="item",
                                quantity=1,
                                unitPrice=1000,
                                discountedUnitPrice=1000,
                                combinedUnitPrice=1000,
                                imagePath="https://example.com/item.jpg",
                            )
                        ],
                    )
                ],
            )
        ],
    ).to_dict()
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        return_value={
            "orderList": [
                {
                    "orderId": 20,
                    "title": "second",
                    "orderedAt": 2,
                    "deliveryGroupList": [
                        {
                            "shipmentBoxId": "B",
                            "invoiceNumber": "2",
                            "invoiceStatus": "INSTRUCT",
                            "pddMessage": {"message": "ready"},
                            "productList": [
                                {
                                    "vendorItemId": 202,
                                    "vendorItemName": "item2",
                                    "productName": "item2",
                                    "quantity": 1,
                                    "unitPrice": 2000,
                                    "discountedUnitPrice": 2000,
                                    "combinedUnitPrice": 2000,
                                    "imagePath": "https://example.com/item2.jpg",
                                }
                            ],
                        }
                    ],
                    "totalProductPrice": 2000,
                }
            ],
            "orderPagination": {"hasNext": False, "nextPageIndex": 0},
        }
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(failed_only=True))
    payload = result.payload

    assert payload.meta.failedPages == []
    assert [order.orderId for order in payload.orders] == [10, 20]
    assert payload.meta.summary == CoupangOrderSummary(
        totalOrders=2,
        addedOrders=1,
        updatedOrders=0,
        deletedOrders=0,
    )
    assert store._orders == payload.to_dict()
    tab.get.assert_any_await(
        "https://mc.coupang.com/ssr/desktop/order/list?requestYear=2026&pageIndex=1"
    )
    assert result.message == "주문 수집 완료: 총 2건, 추가 1건, 변경 0건, 삭제 0건"


@pytest.mark.anyio
async def test_collect_orders_failed_only_keeps_failed_pages_when_retry_fails(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    store._orders = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="old",
            years=["2026"],
            failedPages=[["2026", 1]],
            refresh=False,
            summary=CoupangOrderSummary(
                totalOrders=0,
                addedOrders=0,
                updatedOrders=0,
                deletedOrders=0,
            ),
        ),
        orders=[],
    ).to_dict()
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            RuntimeError("boom"),
            RuntimeError("boom"),
            RuntimeError("boom"),
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(failed_only=True))

    assert result.payload.meta.failedPages == [["2026", 1]]
    assert result.payload.orders == []
    assert result.message == "주문 수집 완료: 총 0건, 추가 0건, 변경 0건, 삭제 0건, 실패 1페이지(2026년 1페이지)"


@pytest.mark.anyio
async def test_collect_orders_unwraps_nodriver_evaluate_payloads(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            [
                {"type": "string", "value": "최근 6개월"},
                {"type": "string", "value": "2026"},
            ],
            {
                "type": "object",
                "value": [
                    ["orderList", {"type": "array", "value": []}],
                    [
                        "orderPagination",
                        {
                            "type": "object",
                            "value": [
                                ["hasNext", {"type": "boolean", "value": False}],
                                ["nextPageIndex", {"type": "number", "value": 0}],
                            ],
                        },
                    ],
                ],
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.payload.meta.years == ["2026"]
    assert result.payload.meta.summary.totalOrders == 0


@pytest.mark.anyio
async def test_collect_orders_retries_when_evaluate_returns_exception_details(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            ExceptionDetails("Uncaught", "Error: missing __NEXT_DATA__"),
            {
                "orderList": [],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.payload.meta.years == ["2026"]
    assert result.payload.meta.summary.totalOrders == 0


@pytest.mark.anyio
async def test_collect_orders_waits_for_order_page_payload_after_navigation(tmp_path: Path) -> None:
    store = _StoreStub(tmp_path)
    browser = Mock()
    session = Mock()
    tab = Mock()
    session.tab = tab
    tab.get = AsyncMock()
    browser.launch = AsyncMock(return_value=session)
    browser.close = AsyncMock()
    tab.evaluate = AsyncMock(
        side_effect=[
            [],
            ["최근 6개월", "2026"],
            ExceptionDetails("Uncaught", "Error: missing __NEXT_DATA__"),
            {
                "orderList": [],
                "orderPagination": {"hasNext": False, "nextPageIndex": 0},
            },
        ]
    )

    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    result = await service.sync_orders(OrderSyncRequest(refresh=True))

    assert result.payload.meta.failedPages == []
    assert result.payload.meta.summary.totalOrders == 0
