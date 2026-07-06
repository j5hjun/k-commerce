from pathlib import Path

from fastapi.testclient import TestClient

from k_commerce_agent.main import create_app
from k_commerce_agent.routes.chat import memory_store


def test_memory_api_returns_session_summary(tmp_path: Path) -> None:
    memory_store.path = tmp_path / "agent-memory.json"
    memory_store._sessions = {}
    memory_store._loaded = True
    memory_store.ingest_history("session-test", ["생수 최저가 추천해줘", "로켓배송이면 좋겠어"])
    memory_store.note_recommendations("session-test", ["삼다수 2L 12개"])

    client = TestClient(create_app())
    response = client.get("/api/memory/session-test")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-test"
    assert "생수" in payload["preferred_categories"]
    assert payload["recent_recommendations"] == ["삼다수 2L 12개"]


def test_orders_api_returns_grouped_order_rows(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "message": "ok",
                      "payload": {
                        "meta": {"collectedAt": "2026-07-05T18:00:00Z"},
                        "orders": [
                          {
                            "orderId": 12345,
                            "orderedAt": 1751635200000,
                            "totalProductPrice": 25980,
                            "deliveryGroupList": [
                              {
                                "shipmentBoxId": "1076368383995285506",
                                "invoiceStatus": "배송완료",
                                "invoiceNumber": "10323394317202",
                                "pddMessage": {"message": "어제(토) 도착"},
                                "productList": [
                                  {
                                    "productName": "Qiaokao 철제 서랍형 수납박스",
                                    "combinedUnitPrice": 25980,
                                    "quantity": 1,
                                    "productUrl": "https://example.com/p/1",
                                    "imagePath": "https://example.com/p/1.jpg"
                                  }
                                ]
                              }
                            ]
                          }
                        ]
                      }
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "order_list", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.get("/api/orders")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["groups"][0]["order_id"] == "12345"
    assert payload["groups"][0]["shipment_box_id"] == "1076368383995285506"
    assert payload["groups"][0]["raw_status"] == "배송완료"
    assert payload["groups"][0]["invoice_number"] == "10323394317202"
    assert payload["groups"][0]["delivery_message"] == "어제(토) 도착"
    assert payload["groups"][0]["items"][0]["product"] == "Qiaokao 철제 서랍형 수납박스"
    assert payload["groups"][0]["items"][0]["price"] == "25,980원"
    assert payload["groups"][0]["items"][0]["image"] == "https://example.com/p/1.jpg"
    assert "reviewable" not in payload["groups"][0]["items"][0]
    assert payload["groups"][0]["year"] == "2025"
    assert payload["groups"][0]["ordered_at"] == 1751635200000


def test_provider_login_status_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "logged_in": true,
                      "message": "이미 로그인되어 있습니다."
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "login_status", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.get("/api/providers/coupang/login-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "provider": "coupang",
        "logged_in": True,
        "message": "이미 로그인되어 있습니다.",
    }


def test_provider_login_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "브라우저를 열었습니다. 로그인 후 다시 확인하세요."
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "login", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.post("/api/providers/coupang/login")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "provider": "coupang",
        "success": True,
        "message": "브라우저를 열었습니다. 로그인 후 다시 확인하세요.",
    }


def test_cart_cache_api_reads_local_json(tmp_path: Path, monkeypatch) -> None:
    provider_root = tmp_path / ".k-commerce" / "coupang"
    provider_root.mkdir(parents=True)
    (provider_root / "cart.json").write_text(
        """
        {
          "meta": {
            "provider": "coupang",
            "collectedAt": "2026-07-06T12:00:00+09:00",
            "refresh": false
          },
          "provider": "coupang",
          "success": true,
          "message": "장바구니 1개",
          "items": [
            {
              "index": 1,
              "product_name": "Qiaokao 철제 서랍형 수납박스",
              "option_text": "화이트",
              "quantity": 2,
              "unit_price": "12,990원",
              "total_price": "25,980원",
              "product_id": "p1",
              "vendor_item_id": "v1",
              "item_id": "i1",
              "delivery_text": "내일(화) 도착"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    client = TestClient(create_app())
    response = client.get("/api/cart/cache")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["collected_at"] == "2026-07-06T12:00:00+09:00"
    assert payload["items"][0]["product_name"] == "Qiaokao 철제 서랍형 수납박스"
    assert payload["items"][0]["quantity"] == 2


def test_cart_quantity_update_api_delegates_to_tool(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    captured_args = None

    class FakeTool:
        async def ainvoke(self, args):
            nonlocal captured_args
            captured_args = args
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "수량 변경 완료",
                      "quantity": 3,
                      "product_id": "p1",
                      "vendor_item_id": "v1",
                      "item_id": "i1"
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "cart_update_quantity", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.patch(
        "/api/cart/items/quantity",
        json={
            "provider": "coupang",
            "quantity": 3,
            "product_id": "p1",
            "vendor_item_id": "v1",
            "item_id": "i1",
        },
    )

    assert response.status_code == 200
    assert captured_args == {
        "provider": "coupang",
        "quantity": 3,
        "product_id": "p1",
        "vendor_item_id": "v1",
        "item_id": "i1",
    }
    assert response.json()["success"] is True
    assert response.json()["quantity"] == 3


def test_cart_bulk_delete_api_delegates_to_tool(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    captured_args = None

    class FakeTool:
        async def ainvoke(self, args):
            nonlocal captured_args
            captured_args = args
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "선택 삭제 완료",
                      "deleted_count": 2
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "cart_delete_items", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.request(
        "DELETE",
        "/api/cart/items/bulk",
        json={
            "provider": "coupang",
            "items": [
                {"product_id": "p1", "vendor_item_id": "v1", "item_id": "i1"},
                {"product_id": "p2", "vendor_item_id": "v2", "item_id": "i2"},
            ],
        },
    )

    assert response.status_code == 200
    assert captured_args == {
        "provider": "coupang",
        "items": [
            {"product_id": "p1", "vendor_item_id": "v1", "item_id": "i1"},
            {"product_id": "p2", "vendor_item_id": "v2", "item_id": "i2"},
        ],
    }
    assert response.json()["success"] is True
    assert response.json()["deleted_count"] == 2


def test_chat_websocket_returns_distinct_message_for_existing_login(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "이미 쿠팡 로그인 상태입니다."
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "login", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json(
            {
                "session_id": "session-login",
                "messages": [{"role": "user", "content": "로그인 진행해줘"}],
            }
        )
        tool_event = websocket.receive_json()
        token_event = websocket.receive_json()
        done_event = websocket.receive_json()

    assert tool_event == {
        "type": "tool",
        "name": "login",
        "args": {"provider": "coupang"},
    }
    assert token_event == {
        "type": "token",
        "content": "이미 쿠팡 로그인 상태예요.\n\n주문 내역이나 장바구니를 바로 확인할 수 있어요.",
    }
    assert done_event == {"type": "done"}


def test_order_delivery_tracking_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "message": "배송조회 정보를 가져왔습니다",
                      "payload": {
                        "provider": "coupang",
                        "orderId": 12345,
                        "shipmentBoxId": "box-1",
                        "invoiceNumber": "1111",
                        "displayStatus": "배송완료",
                        "courierName": "CJ대한통운",
                        "trackingNumber": "1111",
                        "summary": "어제 도착",
                        "rawLines": ["배송조회", "어제 도착"],
                        "collectedAt": "2026-07-05T20:10:00+09:00",
                        "events": [
                          {
                            "time": "2026-07-04 15:00",
                            "status": "배송완료",
                            "description": "문 앞 배송",
                            "location": "서울"
                          }
                        ]
                      }
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "order_delivery_tracking", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.get("/api/orders/12345/shipments/box-1/tracking")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "coupang"
    assert payload["order_id"] == "12345"
    assert payload["shipment_box_id"] == "box-1"
    assert payload["courier_name"] == "CJ대한통운"
    assert payload["summary"] == "어제 도착"
    assert payload["events"][0]["status"] == "배송완료"


def test_reviewable_reviews_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "ok",
                      "items": [
                        {
                          "index": 1,
                          "product_id": "p1",
                          "product_name": "상품 A",
                          "delivery_date": "2026-07-01",
                          "completed_order_vendor_item_id": "o1",
                          "vendor_item_id": "v1",
                          "review_url": "https://example.com/review"
                        }
                      ]
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "review_list_reviewable", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.get("/api/reviews/reviewable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["items"][0]["product_name"] == "상품 A"


def test_editable_reviews_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [
                {
                    "type": "text",
                    "text": """
                    {
                      "provider": "coupang",
                      "success": true,
                      "message": "ok",
                      "items": [
                        {
                          "index": 1,
                          "review_id": "r1",
                          "product_id": "p1",
                          "order_id": "o1",
                          "product_name": "상품 B",
                          "rating": 4,
                          "review_text": "기존 리뷰",
                          "modify_url": "https://example.com/modify"
                        }
                      ]
                    }
                    """,
                }
            ]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "review_list_editable", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.get("/api/reviews/editable")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["items"][0]["review_id"] == "r1"


def test_review_create_api_returns_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class FakeTool:
        async def ainvoke(self, _args):
            return [{"type": "text", "text": '{"provider":"coupang","success":true,"message":"쿠팡 리뷰 업로드 성공","order_id":"o1","product_id":"p1"}'}]

    async def fake_load_tools():
        return [type("Tool", (), {"name": "review_upload", "ainvoke": FakeTool().ainvoke})()]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    response = client.post(
        "/api/reviews",
        json={
            "provider": "coupang",
            "order_id": "o1",
            "product_id": "p1",
            "rating": 5,
            "text": "좋아요",
            "review_url": "https://example.com/review",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_review_edit_and_delete_api_return_tool_payload(monkeypatch) -> None:
    from k_commerce_agent.routes import chat as chat_route

    class EditTool:
        async def ainvoke(self, _args):
            return [{"type": "text", "text": '{"provider":"coupang","success":true,"message":"쿠팡 리뷰 수정 성공","order_id":"o1","product_id":"p1","review_id":"r1"}'}]

    class DeleteTool:
        async def ainvoke(self, _args):
            return [{"type": "text", "text": '{"provider":"coupang","success":true,"message":"쿠팡 리뷰 삭제 성공","order_id":"o1","product_id":"p1","review_id":"r1"}'}]

    async def fake_load_tools():
        return [
            type("Tool", (), {"name": "review_edit", "ainvoke": EditTool().ainvoke})(),
            type("Tool", (), {"name": "review_delete", "ainvoke": DeleteTool().ainvoke})(),
        ]

    monkeypatch.setattr(chat_route, "load_tools", fake_load_tools)

    client = TestClient(create_app())
    edit_response = client.patch(
        "/api/reviews/r1",
        json={
          "provider": "coupang",
          "order_id": "o1",
          "product_id": "p1",
          "rating": 5,
          "text": "수정함"
        },
    )
    delete_response = client.request(
        "DELETE",
        "/api/reviews/r1",
        json={
          "provider": "coupang",
          "order_id": "o1",
          "product_id": "p1"
        },
    )

    assert edit_response.status_code == 200
    assert edit_response.json()["success"] is True
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
