from pathlib import Path

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.orders import CoupangOrderService
from k_commerce_cli.services.providers.coupang.types import (
    CoupangOrderList,
    CoupangOrderMeta,
    CoupangOrderResult,
    CoupangOrderSummary,
)
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import ToolRequestError, ToolRuntimeOptions
from k_commerce_cli.services.types import (
    OrderDetailRequest,
    OrderFailuresRequest,
    OrderListRequest,
    OrderSearchRequest,
    OrderSyncRequest,
    ProviderName,
)


class _StoreStub:
    def __init__(self, root_dir: Path, *, orders: dict | None = None) -> None:
        self.paths = ProviderPaths("coupang", root_dir)
        self.base_dir = self.paths.base_dir
        self.profile_dir = self.paths.profile_dir
        self.cookies_file = self.paths.cookies_file
        self.credentials_path = self.paths.credentials_path
        self.session_meta_path = self.paths.session_meta_path
        self.orders_path = self.paths.orders_path
        self._orders = orders

    def load_credentials(self):
        return None

    def has_session(self) -> bool:
        return False

    def clear_session(self) -> bool:
        return False

    def write_session_metadata(self, payload):
        return None

    def load_orders(self):
        return self._orders

    def write_orders(self, payload):
        self._orders = payload


class _FakeProvider:
    def __init__(self) -> None:
        self.order_list_request: OrderListRequest | None = None
        self.order_search_request: OrderSearchRequest | None = None
        self.order_sync_request: OrderSyncRequest | None = None

    async def list_orders(self, request: OrderListRequest):
        self.order_list_request = request
        return request

    async def sync_orders(self, request: OrderSyncRequest):
        self.order_sync_request = request
        return request

    async def search_orders(self, request: OrderSearchRequest):
        self.order_search_request = request
        return request


def _snapshot() -> dict:
    payload = CoupangOrderList(
        meta=CoupangOrderMeta(
            provider=ProviderName.COUPANG,
            collectedAt="2026-07-06T12:00:00+09:00",
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
            CoupangOrderResult.from_dict(
                {
                    "provider": "coupang",
                    "orderId": 100,
                    "title": "old",
                    "orderedAt": 1767225600000,
                    "totalProductPrice": 1000,
                    "deliveryGroupList": [
                        {
                            "shipmentBoxId": "box-100",
                            "invoiceNumber": "invoice-100",
                            "invoiceStatus": "CANCEL",
                            "pddMessage": {"message": "cancelled"},
                            "productList": [
                                {
                                    "vendorItemId": 102,
                                    "productId": 1002,
                                    "itemId": 2002,
                                    "vendorItemName": "old item",
                                    "productName": "old item",
                                    "quantity": 1,
                                    "unitPrice": 1000,
                                    "discountedUnitPrice": 1000,
                                    "combinedUnitPrice": 1000,
                                    "imagePath": "https://image.example/old.jpg",
                                    "productUrl": "https://www.coupang.com/vp/products/1002?itemId=2002&vendorItemId=102",
                                }
                            ],
                        }
                    ],
                }
            ),
            CoupangOrderResult.from_dict(
                {
                    "provider": "coupang",
                    "orderId": 200,
                    "title": "recent",
                    "orderedAt": 1780272000000,
                    "totalProductPrice": 2000,
                    "deliveryGroupList": [
                        {
                            "shipmentBoxId": "box-200",
                            "invoiceNumber": "invoice-200",
                            "invoiceStatus": "FINAL_DELIVERY",
                            "pddMessage": {"message": "done"},
                            "productList": [
                                {
                                    "vendorItemId": 101,
                                    "productId": 1001,
                                    "itemId": 2001,
                                    "vendorItemName": "recent item",
                                    "productName": "recent item",
                                    "quantity": 1,
                                    "unitPrice": 2000,
                                    "discountedUnitPrice": 2000,
                                    "combinedUnitPrice": 2000,
                                    "imagePath": "https://image.example/recent.jpg",
                                    "productUrl": "https://www.coupang.com/vp/products/1001?itemId=2001&vendorItemId=101",
                                }
                            ],
                        }
                    ],
                }
            ),
        ],
    )
    return payload.to_dict()


@pytest.mark.anyio
async def test_order_list_reads_saved_snapshot_without_launching_browser_when_orders_exist(tmp_path: Path) -> None:
    # Given: saved orders and a browser object that must not be launched.
    store = _StoreStub(tmp_path, orders=_snapshot())
    browser = object()
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=browser)

    # When: the list-only order tool reads a bounded period.
    result = await service.list_orders(
        OrderListRequest(
            start_date="2026-06-01",
            end_date="2026-06-30",
            status="all",
            limit=50,
            cursor=None,
        )
    )

    # Then: only matching saved orders are returned and no collection side effect is required.
    assert result.success is True
    assert result.total_count == 1
    assert result.payload is not None
    assert result.payload.orders[0].orderId == 200
    assert result.payload.orders[0].title == "recent"
    assert result.payload.orders[0].deliveryGroupList[0].productList[0].productUrl == (
        "https://www.coupang.com/vp/products/1001?itemId=2001&vendorItemId=101"
    )
    assert result.next_tools == ()


@pytest.mark.anyio
async def test_order_detail_returns_product_identifiers_and_urls(tmp_path: Path) -> None:
    # Given: a saved order snapshot with product identifiers and product URL.
    store = _StoreStub(tmp_path, orders=_snapshot())
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=object())

    # When: the detail tool reads the saved order.
    result = await service.get_order_detail(OrderDetailRequest(order_id="200"))

    # Then: the payload has the identifiers and URL needed for follow-up tools or direct inspection.
    assert result.success is True
    assert result.payload is not None
    assert result.payload.orders[0].orderId == 200
    product = result.payload.orders[0].deliveryGroupList[0].productList[0]
    assert product.vendorItemId == 101
    assert product.productId == 1001
    assert product.itemId == 2001
    assert product.productUrl == "https://www.coupang.com/vp/products/1001?itemId=2001&vendorItemId=101"
    assert product.imagePath == "https://image.example/recent.jpg"


@pytest.mark.anyio
async def test_order_failures_return_actionable_summary_fields(tmp_path: Path) -> None:
    # Given: a saved snapshot containing a failed order with product details.
    store = _StoreStub(tmp_path, orders=_snapshot())
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=object())

    # When: the failure-list tool reads saved failed orders.
    result = await service.list_order_failures(OrderFailuresRequest(limit=10))

    # Then: the failed order summary keeps the order key and representative product URL.
    assert result.success is True
    assert result.payload is not None
    assert result.payload.orders[0].orderId == 100
    assert result.payload.orders[0].totalProductPrice == 1000
    assert result.payload.orders[0].deliveryGroupList[0].productList[0].productUrl == (
        "https://www.coupang.com/vp/products/1002?itemId=2002&vendorItemId=102"
    )


@pytest.mark.anyio
async def test_order_list_reports_sync_required_when_snapshot_is_missing(tmp_path: Path) -> None:
    # Given: no saved order snapshot.
    store = _StoreStub(tmp_path)
    service = CoupangOrderService(provider=ProviderName.COUPANG, store=store, browser=object())

    # When: the list-only order tool is called.
    result = await service.list_orders(OrderListRequest())

    # Then: the result tells the model to collect orders first.
    assert result.success is False
    assert result.error_code == "sync_required"
    assert result.retryable is False
    assert result.next_tools == ("order_sync",)


@pytest.mark.anyio
async def test_order_dispatch_separates_list_and_sync_requests(tmp_path: Path) -> None:
    # Given: a provider factory that records typed order requests.
    provider = _FakeProvider()

    def get_provider(provider_name: str, root_dir: Path | None = None, terminal=None):
        assert provider_name == "coupang"
        assert root_dir == tmp_path
        assert terminal is None
        return provider

    options = ToolRuntimeOptions(get_provider=get_provider, root_dir=tmp_path)

    # When: list and sync tools are invoked through the shared dispatcher.
    list_result = await invoke_tool(
        "order_list",
        {
            "provider": "coupang",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "status": "all",
            "limit": 25,
            "cursor": "50",
        },
        runtime_options=options,
    )
    sync_result = await invoke_tool(
        "order_sync",
        {
            "provider": "coupang",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "failed_only": False,
            "refresh": True,
        },
        runtime_options=options,
    )

    # Then: list never carries browser collection flags and sync owns them.
    assert list_result == OrderListRequest(
        start_date="2026-06-01",
        end_date="2026-06-30",
        status="all",
        limit=25,
        cursor="50",
    )
    assert sync_result == OrderSyncRequest(
        start_date="2026-01-01",
        end_date="2026-06-30",
        failed_only=False,
        refresh=True,
    )


@pytest.mark.anyio
async def test_order_search_dispatch_builds_typed_search_request(tmp_path: Path) -> None:
    # Given: a provider factory that records typed order search requests.
    provider = _FakeProvider()

    def get_provider(provider_name: str, root_dir: Path | None = None, terminal=None):
        assert provider_name == "coupang"
        return provider

    # When: order_search is invoked through the shared dispatcher.
    result = await invoke_tool(
        "order_search",
        {
            "provider": "coupang",
            "keyword": "세제",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "limit": 25,
        },
        runtime_options=ToolRuntimeOptions(get_provider=get_provider, root_dir=tmp_path),
    )

    # Then: the provider receives a typed search request.
    assert result == OrderSearchRequest(
        keyword="세제",
        start_date="2026-01-01",
        end_date="2026-06-30",
        limit=25,
    )


@pytest.mark.anyio
async def test_order_list_rejects_old_collection_flags_before_dispatch(tmp_path: Path) -> None:
    # Given: the old mixed order_list payload shape.
    provider = _FakeProvider()

    def get_provider(provider_name: str, root_dir: Path | None = None, terminal=None):
        return provider

    # When / Then: validation fails before provider dispatch.
    with pytest.raises(ToolRequestError, match="refresh"):
        await invoke_tool(
            "order_list",
            {"provider": "coupang", "refresh": True},
            runtime_options=ToolRuntimeOptions(get_provider=get_provider, root_dir=tmp_path),
        )
    assert provider.order_list_request is None


@pytest.mark.anyio
async def test_order_detail_and_failures_dispatch_builds_typed_requests(tmp_path: Path) -> None:
    # Given: a provider with detail and failure request recording methods.
    class Provider(_FakeProvider):
        def __init__(self) -> None:
            super().__init__()
            self.order_detail_request: OrderDetailRequest | None = None
            self.order_failures_request: OrderFailuresRequest | None = None

        async def get_order_detail(self, request: OrderDetailRequest):
            self.order_detail_request = request
            return request

        async def list_order_failures(self, request: OrderFailuresRequest):
            self.order_failures_request = request
            return request

    provider = Provider()

    def get_provider(provider_name: str, root_dir: Path | None = None, terminal=None):
        return provider

    options = ToolRuntimeOptions(get_provider=get_provider, root_dir=tmp_path)

    # When: detail and failure tools are invoked through the shared dispatcher.
    detail_result = await invoke_tool(
        "order_detail",
        {"provider": "coupang", "order_id": "100"},
        runtime_options=options,
    )
    failures_result = await invoke_tool(
        "order_failures",
        {"provider": "coupang", "start_date": "2026-01-01", "end_date": "2026-06-30", "limit": 10},
        runtime_options=options,
    )

    # Then: each tool gets its own typed request object.
    assert detail_result == OrderDetailRequest(order_id="100")
    assert failures_result == OrderFailuresRequest(start_date="2026-01-01", end_date="2026-06-30", limit=10)
