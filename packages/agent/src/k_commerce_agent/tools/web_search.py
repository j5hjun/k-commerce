import asyncio
import json
from typing import Any

from ddgs import DDGS
from langchain_core.tools import tool


def _search_sync(query: str, max_results: int) -> list[dict[str, Any]]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """웹을 검색합니다.

    MCP 도구(쿠팡 검색/주문/장바구니 등)로 확인할 수 없는 정보를 찾을 때 사용하는
    fallback 도구입니다. 예: 상품의 상세 스펙/리뷰 요약처럼 검색 결과 목록에 없는
    정보, 다른 쇼핑몰과의 비교, 최신 뉴스 등. 반환된 결과(제목/URL/요약)는 다음
    도구 호출의 입력으로 이어서 활용할 수 있습니다.
    """

    results = await asyncio.to_thread(_search_sync, query, max_results)
    payload = {
        "query": query,
        "item_count": len(results),
        "items": [
            {
                "index": index,
                "title": str(result.get("title") or "").strip(),
                "url": str(result.get("href") or "").strip(),
                "snippet": str(result.get("body") or "").strip(),
            }
            for index, result in enumerate(results, start=1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False)
