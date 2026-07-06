from dataclasses import dataclass
from pathlib import Path

import pytest

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.types import JSONValue, ToolRequestError, ToolRuntimeOptions
from k_commerce_cli.services.types import (
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ProviderName,
    ReviewUploadRequest,
    ReviewUploadResult,
    StatusResult,
)
from k_commerce_cli.services.registry import list_providers

ProviderRequest = CartQuantityUpdateRequest | ReviewUploadRequest | None


@dataclass(frozen=True)
class ProviderCall:
    name: str
    request: ProviderRequest = None


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[ProviderCall] = []

    async def status(self) -> StatusResult:
        self.calls.append(ProviderCall("status"))
        return StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
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

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        self.calls.append(ProviderCall("upload_review", request))
        return ReviewUploadResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 리뷰 작성 성공",
            order_id=request.order_id,
            product_id=request.product_id,
        )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def runtime_options(fake_provider: FakeProvider) -> ToolRuntimeOptions:
    def get_provider(
        provider: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> FakeProvider:
        assert provider == "coupang"
        assert root_dir == Path("/tmp/k-commerce-test")
        assert terminal is None
        return fake_provider

    return ToolRuntimeOptions(
        get_provider=get_provider,
        list_providers=list_providers,
        root_dir=Path("/tmp/k-commerce-test"),
    )


@pytest.mark.anyio
async def test_status_delegates_to_provider_when_payload_is_valid(
    fake_provider: FakeProvider,
    runtime_options: ToolRuntimeOptions,
) -> None:
    # Given: a canonical status request.
    # When: the shared invoker receives it.
    result = await invoke_tool(
        "status",
        {"provider": "coupang"},
        runtime_options=runtime_options,
    )

    # Then: the provider status method is called and its dataclass result is returned.
    assert result == StatusResult(
        provider=ProviderName.COUPANG,
        logged_in=True,
        message="쿠팡 로그인 상태입니다",
    )
    assert fake_provider.calls == [ProviderCall("status")]


@pytest.mark.anyio
async def test_cart_update_quantity_builds_dataclass_request_when_payload_is_valid(
    fake_provider: FakeProvider,
    runtime_options: ToolRuntimeOptions,
) -> None:
    # Given: a canonical cart quantity request.
    payload = {
        "provider": "coupang",
        "quantity": 3,
        "product_id": "p",
        "vendor_item_id": "v",
        "item_id": "i",
    }

    # When: the shared invoker receives it.
    await invoke_tool("cart_update_quantity", payload, runtime_options=runtime_options)

    # Then: the provider receives the existing service request dataclass.
    assert fake_provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(
                quantity=3,
                product_id="p",
                vendor_item_id="v",
                item_id="i",
            ),
        )
    ]


@pytest.mark.anyio
async def test_review_upload_builds_dataclass_request_when_payload_is_valid(
    fake_provider: FakeProvider,
    runtime_options: ToolRuntimeOptions,
) -> None:
    # Given: a canonical review upload request.
    payload = {
        "provider": "coupang",
        "order_id": "o",
        "product_id": "p",
        "rating": 5,
        "text": "좋아요",
        "review_url": "https://example.test/review",
    }

    # When: the shared invoker receives it.
    await invoke_tool("review_upload", payload, runtime_options=runtime_options)

    # Then: the provider receives the existing service request dataclass.
    assert fake_provider.calls == [
        ProviderCall(
            "upload_review",
            ReviewUploadRequest(
                order_id="o",
                product_id="p",
                rating=5,
                text="좋아요",
                review_url="https://example.test/review",
            ),
        )
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "payload", "match"),
    [
        ("unknown_tool", {"provider": "coupang"}, "Unknown tool"),
        ("status", ["coupang"], "Payload must be a JSON object"),
        ("status", {"provider": "coupang", "root_dir": "/tmp"}, "root_dir"),
        (
            "order_sync",
            {"provider": "coupang", "refresh": True, "failed_only": True},
            "refresh and failed_only",
        ),
        (
            "cart_update_quantity",
            {"provider": "coupang", "quantity": 0},
            "quantity",
        ),
        (
            "cart_delete_items",
            {"provider": "coupang", "items": []},
            "items",
        ),
    ],
)
async def test_invalid_requests_fail_before_dispatch_when_payload_is_invalid(
    tool_name: str,
    payload: JSONValue,
    match: str,
    fake_provider: FakeProvider,
    runtime_options: ToolRuntimeOptions,
) -> None:
    # Given: malformed or non-canonical input.
    # When / Then: validation raises a typed tool error before service dispatch.
    with pytest.raises(ToolRequestError, match=match):
        await invoke_tool(tool_name, payload, runtime_options=runtime_options)
    assert fake_provider.calls == []
