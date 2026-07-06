from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest
from k_commerce_cli.base import Terminal
from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.tools import ToolRequestError
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    OrderListRequest,
    OrderListResult,
    OrderSearchRequest,
    OrderSearchResult,
    ProviderName,
    ReviewUploadRequest,
    ReviewUploadResult,
    StatusResult,
)
from k_commerce_mcp import server
from k_commerce_mcp.tools.cart import cart_delete_items, cart_update_quantity
from k_commerce_mcp.tools.order import order_list, order_search
from k_commerce_mcp.tools.review import review_upload
from k_commerce_mcp.tools.search import search_products
from k_commerce_mcp.tools.status import status

ProviderFactory = Callable[[str, Path | None, Terminal | None], "RecordingProvider"]


@dataclass(slots=True)
class RecordingProvider:
    factory_calls: list[tuple[str, Path | None, bool]] = field(default_factory=list)
    status_calls: int = 0
    order_list_request: OrderListRequest | None = None
    order_search_request: OrderSearchRequest | None = None
    search_call: tuple[str, str | None, str, int] | None = None
    cart_quantity_request: CartQuantityUpdateRequest | None = None
    cart_delete_requests: tuple[CartDeleteRequest, ...] | None = None
    review_upload_request: ReviewUploadRequest | None = None

    async def status(self) -> StatusResult:
        self.status_calls += 1
        return StatusResult(provider=ProviderName.COUPANG, logged_in=True, message="logged in")

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> SearchProductResult:
        self.search_call = (keyword, category, sort, max_results)
        return SearchProductResult(provider="coupang", success=True, message="found", items=())

    async def list_orders(self, request: OrderListRequest) -> OrderListResult:
        self.order_list_request = request
        return OrderListResult(
            success=True,
            provider="coupang",
            message="saved orders",
            start_date=request.start_date,
            end_date=request.end_date,
            count=0,
            total_count=0,
            has_more=False,
            next_cursor=None,
            orders=(),
        )

    async def search_orders(self, request: OrderSearchRequest) -> OrderSearchResult:
        self.order_search_request = request
        return OrderSearchResult(
            success=True,
            provider="coupang",
            message="searched orders",
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            count=0,
            total_count=0,
            orders=(),
        )

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.cart_quantity_request = request
        return CartQuantityUpdateResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="updated",
            quantity=request.quantity,
            product_id=request.product_id,
            vendor_item_id=request.vendor_item_id,
            item_id=request.item_id,
        )

    async def delete_cart_items(
        self,
        requests: tuple[CartDeleteRequest, ...],
    ) -> CartDeleteResult:
        self.cart_delete_requests = requests
        return CartDeleteResult(provider=ProviderName.COUPANG, success=True, message="deleted", deleted_count=len(requests))

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        self.review_upload_request = request
        return ReviewUploadResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="uploaded",
            order_id=request.order_id,
            product_id=request.product_id,
        )


@dataclass(slots=True)
class RecordingMcpServer:
    transport: str | None = None

    def run(self, *, transport: str) -> None:
        self.transport = transport


def provider_factory(provider: RecordingProvider) -> ProviderFactory:
    def build_provider(
        provider_name: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> RecordingProvider:
        provider.factory_calls.append((provider_name, root_dir, terminal is not None))
        return provider

    return build_provider


@pytest.mark.anyio
async def test_create_mcp_server_registers_canonical_tools_only() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert tool_names == {
        "get_providers",
        "login",
        "status",
        "logout",
        "order_sync",
        "order_list",
        "order_search",
        "order_detail",
        "order_failures",
        "cart_list",
        "cart_update_quantity",
        "cart_delete_item",
        "cart_delete_items",
        "cart_clear",
        "search_products",
        "review_list_reviewable",
        "review_list_editable",
        "review_upload",
        "review_edit",
        "review_delete",
    }


@pytest.mark.anyio
async def test_status_tool_delegates_to_provider_through_shared_invocation() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await status(provider="coupang")

    assert result == StatusResult(provider=ProviderName.COUPANG, logged_in=True, message="logged in")
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.status_calls == 1


@pytest.mark.anyio
async def test_order_list_tool_delegates_canonical_fields_to_provider() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await order_list(
            provider="coupang",
            start_date="2026-06-01",
            end_date="2026-06-30",
            status="all",
            limit=25,
            cursor="50",
        )

    assert result == OrderListResult(
        success=True,
        provider="coupang",
        message="saved orders",
        start_date="2026-06-01",
        end_date="2026-06-30",
        count=0,
        total_count=0,
        has_more=False,
        next_cursor=None,
        orders=(),
    )
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.order_list_request == OrderListRequest(
        start_date="2026-06-01",
        end_date="2026-06-30",
        status="all",
        limit=25,
        cursor="50",
    )


@pytest.mark.anyio
async def test_order_search_tool_delegates_canonical_fields_to_provider() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await order_search(
            provider="coupang",
            keyword="coffee",
            start_date="2026-06-01",
            end_date="2026-06-30",
            limit=25,
        )

    assert result == OrderSearchResult(
        success=True,
        provider="coupang",
        message="searched orders",
        keyword="coffee",
        start_date="2026-06-01",
        end_date="2026-06-30",
        count=0,
        total_count=0,
        orders=(),
    )
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.order_search_request == OrderSearchRequest(
        keyword="coffee",
        start_date="2026-06-01",
        end_date="2026-06-30",
        limit=25,
    )


@pytest.mark.anyio
async def test_search_tool_delegates_canonical_fields_to_provider() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await search_products(
            provider="coupang",
            keyword="coffee",
            category="food",
            sort="low_price",
            max_results=5,
        )

    assert result == SearchProductResult(provider="coupang", success=True, message="found", items=())
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.search_call == ("coffee", "food", "low_price", 5)


@pytest.mark.anyio
async def test_cart_quantity_tool_builds_provider_request_dataclass() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await cart_update_quantity(
            provider="coupang",
            quantity=3,
            product_id="p1",
            vendor_item_id="v1",
            item_id="i1",
        )

    assert result == CartQuantityUpdateResult(
        provider=ProviderName.COUPANG,
        success=True,
        message="updated",
        quantity=3,
        product_id="p1",
        vendor_item_id="v1",
        item_id="i1",
    )
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.cart_quantity_request == CartQuantityUpdateRequest(
        quantity=3,
        product_id="p1",
        vendor_item_id="v1",
        item_id="i1",
    )


@pytest.mark.anyio
async def test_cart_delete_items_tool_builds_provider_request_dataclasses() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await cart_delete_items(
            provider="coupang",
            items=[
                CartDeleteRequest(product_id="p1", vendor_item_id="v1", item_id="i1"),
                CartDeleteRequest(product_id="p2", vendor_item_id="v2", item_id="i2"),
            ],
        )

    assert result == CartDeleteResult(provider=ProviderName.COUPANG, success=True, message="deleted", deleted_count=2)
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.cart_delete_requests == (
        CartDeleteRequest(product_id="p1", vendor_item_id="v1", item_id="i1"),
        CartDeleteRequest(product_id="p2", vendor_item_id="v2", item_id="i2"),
    )


@pytest.mark.anyio
async def test_review_upload_tool_builds_provider_request_dataclass() -> None:
    provider = RecordingProvider()

    with patch("k_commerce_cli.services.tools.invoke.default_get_provider", new=provider_factory(provider)):
        result = await review_upload(
            provider="coupang",
            order_id="o1",
            product_id="p1",
            rating=5,
            text="좋아요",
            review_url="https://example.test/review",
        )

    assert result == ReviewUploadResult(
        provider=ProviderName.COUPANG,
        success=True,
        message="uploaded",
        order_id="o1",
        product_id="p1",
    )
    assert provider.factory_calls == [("coupang", None, False)]
    assert provider.review_upload_request == ReviewUploadRequest(
        order_id="o1",
        product_id="p1",
        rating=5,
        text="좋아요",
        review_url="https://example.test/review",
    )


@pytest.mark.anyio
async def test_cart_delete_items_tool_surfaces_shared_validation_errors() -> None:
    with pytest.raises(ToolRequestError) as exc_info:
        _ = await cart_delete_items(provider="coupang", items=[])

    assert exc_info.value == ToolRequestError(
        "cart_delete_items",
        "items must be a non-empty list",
        field="items",
        error_code="invalid_field",
    )


def test_main_runs_mcp_server_over_stdio() -> None:
    created_servers: list[RecordingMcpServer] = []

    def create_fake_server() -> RecordingMcpServer:
        fake_server = RecordingMcpServer()
        created_servers.append(fake_server)
        return fake_server

    with patch("k_commerce_mcp.server.create_mcp_server", new=create_fake_server):
        server.main()

    assert len(created_servers) == 1
    assert created_servers[0].transport == "stdio"
