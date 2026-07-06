from dataclasses import dataclass
from enum import StrEnum

import pytest

from k_commerce_cli.services.tools.registry import (
    get_tool_definition,
    list_tool_names,
)
from k_commerce_cli.services.tools.serialization import to_jsonable


CANONICAL_TOOL_NAMES = [
    "get_providers",
    "login",
    "status",
    "logout",
    "order_list",
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
]


class ExampleProvider(StrEnum):
    COUPANG = "coupang"


@dataclass(frozen=True)
class NestedResult:
    provider: ExampleProvider
    message: str
    items: tuple[int, ...]


def test_list_tool_names_returns_canonical_contract_when_requested() -> None:
    # Given: the canonical shared commerce tool contract.
    # When: callers list available tool names.
    names = list_tool_names()

    # Then: the list is exact, stable, and excludes the old non-canonical name.
    assert names == CANONICAL_TOOL_NAMES
    assert "login_status" not in names


def test_get_tool_definition_rejects_login_status_when_requested() -> None:
    # Given: the old login_status name is not canonical.
    # When / Then: looking it up fails at the registry boundary.
    with pytest.raises(KeyError):
        get_tool_definition("login_status")


def test_to_jsonable_preserves_nested_dataclasses_and_korean_text_when_requested() -> None:
    # Given: nested service-style dataclasses with enums and tuples.
    result = {
        "message": "쿠팡 로그인 상태입니다",
        "result": NestedResult(
            provider=ExampleProvider.COUPANG,
            message="장바구니 상품",
            items=(1, 2),
        ),
    }

    # When: the result is converted for JSON output.
    jsonable = to_jsonable(result)

    # Then: Korean text is preserved and non-JSON containers become JSON-compatible.
    assert jsonable == {
        "message": "쿠팡 로그인 상태입니다",
        "result": {
            "provider": "coupang",
            "message": "장바구니 상품",
            "items": [1, 2],
        },
    }
