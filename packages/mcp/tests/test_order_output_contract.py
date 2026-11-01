import json
import pickle
from dataclasses import asdict, replace
from unittest.mock import AsyncMock

import jsonschema
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from k_commerce_cli.services.providers.coupang.types import CoupangOrderList
from k_commerce_cli.services.types import (
    OrderDetailResult,
    OrderFailuresResult,
    OrderListResult,
    OrderSearchResult,
    OrderSyncResult,
    ProviderName,
)
from k_commerce_cli.services.types.provider import ProviderName as LegacyProviderName
from k_commerce_mcp.server import create_mcp_server
from k_commerce_mcp.tools import order


PAYLOAD = CoupangOrderList.from_dict({
    "meta": {
        "provider": "coupang", "collectedAt": "2026-01-01T00:00:00+09:00", "years": ["2026"],
        "failedPages": [["2025", 2]], "refresh": False,
        "summary": {"totalOrders": 1, "addedOrders": 1, "updatedOrders": 0, "deletedOrders": 0},
    },
    "orders": [{
        "provider": "coupang", "orderId": 123, "title": "example", "orderedAt": 1767225600000,
        "totalProductPrice": 1000, "deliveryGroupList": [{
            "shipmentBoxId": "box", "invoiceNumber": "invoice", "invoiceStatus": "DELIVERED",
            "pddMessage": {"message": None}, "productList": [{
                "vendorItemId": 456, "vendorItemName": "option", "productName": "product", "quantity": 1,
                "unitPrice": 1000, "discountedUnitPrice": 1000, "combinedUnitPrice": 1000,
                "imagePath": "https://example.com/image.png", "productUrl": "https://example.com/product",
                "productId": 789, "itemId": 10,
            }],
        }],
    }],
})

CASES = [
    ("order_sync", {"provider": "coupang"}, OrderSyncResult(True, "coupang", "ok", payload=PAYLOAD)),
    ("order_list", {"provider": "coupang"}, OrderListResult(True, "coupang", "ok", None, None, 1, False, None, PAYLOAD)),
    ("order_search", {"provider": "coupang", "keyword": "example"}, OrderSearchResult(True, "coupang", "ok", "example", None, None, 1, PAYLOAD)),
    ("order_detail", {"provider": "coupang", "order_id": "123"}, OrderDetailResult(True, "coupang", "ok", "123", PAYLOAD)),
    ("order_failures", {"provider": "coupang"}, OrderFailuresResult(True, "coupang", "ok", None, None, PAYLOAD)),
]


def test_provider_enum_preserves_existing_import_identity_and_pickle_roundtrip():
    assert ProviderName is LegacyProviderName
    assert pickle.loads(pickle.dumps(ProviderName.COUPANG)) is ProviderName.COUPANG


@pytest.mark.anyio
@pytest.mark.parametrize("name,arguments,success_result", CASES, ids=[case[0] for case in CASES])
@pytest.mark.parametrize("success", [True, False], ids=["success", "failure"])
async def test_order_tool_exposes_schema_and_preserves_wire_payload(monkeypatch, name, arguments, success_result, success):
    value = success_result if success else replace(success_result, success=False, message="failure", payload=None, error_code="not_logged_in", retryable=True, next_tools=("login",))
    invoke = AsyncMock(return_value=value)
    monkeypatch.setattr(order, "invoke_tool", invoke)

    async with create_connected_server_and_client_session(create_mcp_server()) as client:
        tool = next(item for item in (await client.list_tools()).tools if item.name == name)
        assert tool.outputSchema is not None
        result = await client.call_tool(name, arguments)

    expected = json.loads(json.dumps(asdict(value)))
    assert result.isError is False
    assert result.structuredContent == expected
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert json.loads(result.content[0].text) == expected
    jsonschema.validate(result.structuredContent, tool.outputSchema)
    invoke.assert_awaited_once()


@pytest.mark.parametrize("module", [
    "k_commerce_cli.services.providers.coupang.types",
    "k_commerce_cli.services.types.order",
    "k_commerce_cli.services.types.provider",
    "k_commerce_mcp.server",
])
def test_order_type_imports_do_not_depend_on_import_order(module):
    import subprocess
    import sys

    subprocess.run([sys.executable, "-c", f"import {module}"], check=True, capture_output=True, text=True, timeout=30)
