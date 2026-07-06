import json

from k_commerce_agent.history import (
    compact_tool_result_for_history,
    extract_requested_limit,
    prepare_chat_messages,
    turn_list_limit,
)


def test_compact_tool_result_strips_heavy_editable_fields() -> None:
    raw = json.dumps(
        {
            "provider": "coupang",
            "success": True,
            "message": "리뷰 수정 가능 (2건):\n\n  No ...",
            "items": [
                {
                    "index": 1,
                    "review_id": "111",
                    "product_id": "p1",
                    "order_id": "",
                    "product_name": "상품A",
                    "rating": 5,
                    "review_text": "긴 후기 본문" * 20,
                    "modify_url": "https://example.test/modify",
                }
            ],
        },
        ensure_ascii=False,
    )

    compact = json.loads(compact_tool_result_for_history("review_list_editable", raw))

    assert compact["item_count"] == 1
    item = compact["items"][0]
    assert item["index"] == 1
    assert item["review_id"] == "111"
    assert item["product_name"] == "상품A"
    assert item["rating"] == 5
    assert item["written_at"] == ""
    assert "message" not in compact
    assert len(item["review_text"]) <= 120
    assert item["review_text"].endswith("...")


def test_prepare_chat_messages_keeps_only_latest_list_tool_result() -> None:
    first = json.dumps({"success": True, "items": [{"index": 1, "review_id": "1"}]})
    second = json.dumps({"success": True, "items": [{"index": 2, "review_id": "2"}]})
    messages = [
        {"role": "user", "content": "리뷰 목록"},
        {"role": "assistant", "content": f"[review_list_editable 결과] {first}"},
        {"role": "user", "content": "다시"},
        {"role": "assistant", "content": f"[review_list_editable 결과] {second}"},
    ]

    prepared = prepare_chat_messages(messages)

    editable_results = [m for m in prepared if m["content"].startswith("[review_list_editable 결과]")]
    assert len(editable_results) == 1
    assert '"review_id": "2"' in editable_results[0]["content"]


def test_compact_order_list_strips_nested_payload() -> None:
    raw = json.dumps(
        {
            "message": "주문 수집 완료: 총 12건",
            "payload": {
                "meta": {"summary": {"totalOrders": 12}},
                "orders": [
                    {
                        "orderId": 101,
                        "title": "테스트 주문",
                        "orderedAt": 1_704_067_200_000,
                        "totalProductPrice": 4800,
                        "deliveryGroupList": [
                            {
                                "productList": [
                                    {
                                        "vendorItemName": "양산",
                                        "quantity": 1,
                                        "discountedUnitPrice": 4800,
                                        "unitPrice": 10000,
                                        "imagePath": "/should/be/stripped",
                                    }
                                ]
                            }
                        ],
                    }
                ],
            },
        },
        ensure_ascii=False,
    )

    compact = json.loads(compact_tool_result_for_history("order_list", raw))

    assert compact["total_count"] == 12
    assert compact["shown_count"] == 1
    assert compact["items"][0]["order_id"] == 101
    assert compact["items"][0]["products"][0]["name"] == "양산"
    assert "payload" not in compact
    assert "imagePath" not in json.dumps(compact, ensure_ascii=False)


def test_extract_requested_limit_parses_korean_phrases() -> None:
    assert extract_requested_limit("주문목록 상위 5개만") == 5
    assert extract_requested_limit("최근 3건") == 3
    assert extract_requested_limit("주문 보여줘") is None


def test_compact_order_list_respects_turn_list_limit() -> None:
    orders = [{"orderId": index, "title": f"주문{index}", "deliveryGroupList": []} for index in range(1, 8)]
    raw = json.dumps(
        {"payload": {"meta": {"summary": {"totalOrders": 7}}, "orders": orders}},
        ensure_ascii=False,
    )
    token = turn_list_limit.set(5)
    try:
        compact = json.loads(compact_tool_result_for_history("order_list", raw))
    finally:
        turn_list_limit.reset(token)

    assert compact["total_count"] == 7
    assert compact["shown_count"] == 5
    assert len(compact["items"]) == 5


def test_compact_cart_list_keeps_display_fields() -> None:
    raw = json.dumps(
        {
            "provider": "coupang",
            "success": True,
            "message": "장바구니 상품 (2건)",
            "items": [
                {
                    "index": 1,
                    "product_name": "시리얼",
                    "option_text": "620g, 1개",
                    "quantity": 1,
                    "unit_price": "5,760원",
                    "total_price": "5,760원",
                    "product_id": "8281254495",
                }
            ],
        },
        ensure_ascii=False,
    )

    compact = json.loads(compact_tool_result_for_history("cart_list", raw))

    assert compact["item_count"] == 1
    assert compact["items"][0]["option_text"] == "620g, 1개"
    assert compact["items"][0]["total_price"] == "5,760원"
    assert "message" not in compact
