import json
from unittest.mock import patch

import pytest

from k_commerce_agent.tools.web_search import web_search


@pytest.mark.anyio
async def test_web_search_returns_structured_json() -> None:
    fake_results = [
        {
            "title": "라카나스타 통밀 또띠아",
            "href": "https://example.com/product",
            "body": "320g, 2개",
        }
    ]
    with patch("k_commerce_agent.tools.web_search._search_sync", return_value=fake_results):
        raw = await web_search.ainvoke({"query": "통밀또띠아", "max_results": 3})

    parsed = json.loads(raw)
    assert parsed["query"] == "통밀또띠아"
    assert parsed["item_count"] == 1
    assert parsed["items"][0]["title"] == "라카나스타 통밀 또띠아"
    assert parsed["items"][0]["url"] == "https://example.com/product"
    assert parsed["items"][0]["snippet"] == "320g, 2개"


@pytest.mark.anyio
async def test_web_search_empty_results_returns_json() -> None:
    with patch("k_commerce_agent.tools.web_search._search_sync", return_value=[]):
        raw = await web_search.ainvoke({"query": "없는상품", "max_results": 3})

    parsed = json.loads(raw)
    assert parsed["item_count"] == 0
    assert parsed["items"] == []
