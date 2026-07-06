from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from k_commerce_agent.memory import SessionMemory
from k_commerce_agent.recommendations import _build_queries_from_text, run_recommendation_graph


class FakeTool:
    def __init__(self, payload: dict, on_invoke: Callable[[dict], None] | None = None) -> None:
        self.payload = payload
        self.on_invoke = on_invoke

    async def ainvoke(self, args: dict) -> list[dict[str, str]]:
        if self.on_invoke is not None:
            self.on_invoke(args)
        return [{"type": "text", "text": json.dumps(self.payload, ensure_ascii=False)}]


def test_build_queries_from_text_removes_instructional_noise() -> None:
    memory = SessionMemory(session_id="s1")
    queries = _build_queries_from_text(
        "생수 최저가로 추천해줘. 로켓배송이면 좋고 2리터 위주로 봐줘.",
        memory,
        [],
    )

    assert "생수 2리터" in queries
    assert all("최저가" not in query for query in queries)
    assert all("추천" not in query for query in queries)


@pytest.mark.anyio
async def test_recommendation_graph_uses_memory_and_search_results() -> None:
    memory = SessionMemory(session_id="s1")
    memory.ingest_user_message("생수 최저가로 추천해줘")
    search_calls: list[dict] = []

    tools = {
        "cart_list": FakeTool(
            {
                "provider": "coupang",
                "success": True,
                "items": [{"product_name": "삼다수 2L"}],
            }
        ),
        "order_list": FakeTool(
            {
                "message": "ok",
                "payload": {
                    "orders": [
                        {
                            "deliveryGroupList": [
                                {"productList": [{"productName": "백산수 2L"}]}
                            ]
                        }
                    ]
                },
            }
        ),
        "search_products": FakeTool(
            {
                "provider": "coupang",
                "success": True,
                "items": [
                    {
                        "product_id": "p1",
                        "product_name": "삼다수 2L 12개",
                        "price": "11,900원",
                        "rating": "4.9",
                        "product_link": "https://example.com/p1",
                    },
                    {
                        "product_id": "p2",
                        "product_name": "백산수 2L 12개",
                        "price": "13,900원",
                        "rating": "4.8",
                        "product_link": "https://example.com/p2",
                    },
                ],
            },
            on_invoke=search_calls.append,
        ),
    }

    response, names = await run_recommendation_graph(
        user_message="생수 최저가 추천해줘",
        memory=memory,
        tools=tools,
    )

    assert "삼다수 2L 12개" in response
    assert "쿠팡 검색 기준 저가 우선" in response
    assert names[0] == "삼다수 2L 12개"
    assert search_calls
    assert search_calls[0]["keyword"] == "생수"
    assert all("최저가" not in call["keyword"] for call in search_calls)
