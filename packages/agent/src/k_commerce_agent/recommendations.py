from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypedDict

from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from k_commerce_agent.memory import SessionMemory, category_counter
from k_commerce_agent.price_compare import compare_external_prices


ToolEventHandler = Callable[[str, dict[str, Any]], Awaitable[None] | None]
QUERY_STOPWORDS = {
    "추천",
    "추천해줘",
    "비교",
    "비교해줘",
    "최저가",
    "낮은가격순",
    "검색",
    "검색해줘",
    "보여줘",
    "봐줘",
    "찾아줘",
    "말고",
    "방금",
    "같이",
    "쪽도",
    "위주로",
    "좋고",
    "좋겠어",
    "해줘",
    "로켓배송",
}
QUERY_NOISE_PATTERNS = (
    "최저가",
    "추천",
    "비교",
    "검색",
    "보여줘",
    "찾아줘",
    "말고",
    "같이",
    "위주로",
    "좋겠",
    "좋고",
    "방금",
)


class RecommendationState(TypedDict, total=False):
    user_message: str
    memory: SessionMemory
    tools: dict[str, BaseTool]
    on_tool: ToolEventHandler | None
    context: dict[str, Any]
    queries: list[str]
    candidates: list["Candidate"]
    comparisons: dict[str, list[dict[str, Any]]]
    response: str


@dataclass
class Candidate:
    product_id: str
    product_name: str
    price: str
    rating: str
    product_link: str
    score: float
    reasons: list[str]
    source_query: str


def _extract_text_payload(result: Any) -> str:
    if isinstance(result, list):
        texts = [item.get("text", "") for item in result if isinstance(item, dict)]
        return "\n".join(text for text in texts if text)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _parse_tool_result(result: Any) -> dict[str, Any]:
    text = _extract_text_payload(result).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"message": text}


async def _call_tool(
    state: RecommendationState,
    name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    handler = state.get("on_tool")
    if handler is not None:
        maybe_awaitable = handler(name, args)
        if maybe_awaitable is not None:
            await maybe_awaitable

    tool = state["tools"].get(name)
    if tool is None:
        return {"success": False, "message": f"{name} 도구를 찾을 수 없습니다."}

    try:
        return _parse_tool_result(await tool.ainvoke(args))
    except Exception as exc:
        return {"success": False, "message": f"{name} 실행 실패: {exc}"}


def _pick_context_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []

    for item in payload.get("items", []) or []:
        product_name = item.get("product_name") or item.get("productName")
        if product_name:
            names.append(str(product_name))

    orders = ((payload.get("payload") or {}).get("orders")) or []
    for order in orders:
        for group in order.get("deliveryGroupList", []) or []:
            for product in group.get("productList", []) or []:
                product_name = product.get("productName") or product.get("vendorItemName")
                if product_name:
                    names.append(str(product_name))

    return names


def _clean_query_text(text: str) -> str:
    cleaned = text
    for pattern in QUERY_NOISE_PATTERNS:
        cleaned = cleaned.replace(pattern, " ")
    cleaned = re.sub(r"[^\w가-힣\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_search_terms(text: str) -> list[str]:
    cleaned = _clean_query_text(text)
    tokens = []
    for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", cleaned):
        if token in QUERY_STOPWORDS:
            continue
        if token.startswith("로켓배송"):
            continue
        if token.endswith(("해줘", "이면", "위주", "추천", "비교")):
            continue
        tokens.append(token)
    return tokens


def _build_queries_from_text(user_message: str, memory: SessionMemory, context_names: list[str]) -> list[str]:
    tokens = _extract_search_terms(user_message)
    queries: list[str] = []

    if tokens:
        queries.append(" ".join(tokens[:3]))

    category_counts = category_counter([user_message, *memory.user_messages[-2:]])
    for category, _count in category_counts.most_common(3):
        queries.append(category)

    if not queries:
        for name in context_names[:2]:
            name_tokens = _extract_search_terms(name)
            if name_tokens:
                queries.append(" ".join(name_tokens[:3]))

    queries.extend(
        " ".join(_extract_search_terms(query)[:3])
        for query in memory.recent_queries[-4:]
        if _extract_search_terms(query)
    )

    unique_queries: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = query.strip()
        if len(normalized) < 2:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_queries.append(normalized)
    return unique_queries[:4]


def _price_to_number(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def _rating_to_number(value: str) -> float:
    try:
        return float(re.search(r"\d+(?:\.\d+)?", value or "")[0])
    except Exception:
        return 0.0


def _score_candidate(
    item: dict[str, Any],
    query: str,
    memory: SessionMemory,
    context_names: list[str],
) -> Candidate:
    name = str(item.get("product_name") or item.get("productName") or "")
    price = str(item.get("price") or "")
    rating = str(item.get("rating") or "")
    product_id = str(item.get("product_id") or item.get("productId") or "")
    link = str(item.get("product_link") or item.get("productUrl") or "")

    lowered_name = name.lower()
    score = 0.0
    reasons: list[str] = []

    if query and query.lower() in lowered_name:
        score += 2.0
        reasons.append(f"'{query}' 검색과 직접 일치")

    for category in memory.preferred_categories:
        if category in name:
            score += 1.5
            reasons.append(f"{category} 선호 반영")

    for source_name in context_names[:6]:
        if source_name and source_name.split()[0].lower() in lowered_name:
            score += 1.0
            reasons.append("주문/장바구니 연관 상품")
            break

    price_number = _price_to_number(price)
    if price_number is not None:
        if memory.price_preference == "lowest_price":
            score += max(0.0, 2_000_000 - price_number) / 500_000
            reasons.append("낮은 가격 우선")
        elif memory.price_preference == "value":
            score += 1.0
            reasons.append("가성비 고려")

    rating_number = _rating_to_number(rating)
    if rating_number:
        score += rating_number / 5
        reasons.append("리뷰 평점 반영")

    if memory.delivery_preference == "rocket" and "로켓" in name:
        score += 1.0
        reasons.append("빠른 배송 선호 반영")

    for keyword in memory.avoided_keywords:
        if keyword and keyword.lower() in lowered_name:
            score -= 2.0
            reasons.append(f"회피 키워드 '{keyword}' 포함")

    return Candidate(
        product_id=product_id,
        product_name=name,
        price=price,
        rating=rating,
        product_link=link,
        score=score,
        reasons=list(dict.fromkeys(reasons))[:3],
        source_query=query,
    )


async def _load_context_node(state: RecommendationState) -> RecommendationState:
    cart = await _call_tool(state, "cart_list", {"provider": "coupang"})
    orders = await _call_tool(
        state,
        "order_list",
        {"provider": "coupang", "refresh": False, "failed_only": False},
    )
    return {"context": {"cart": cart, "orders": orders}}


async def _build_queries_node(state: RecommendationState) -> RecommendationState:
    context = state.get("context", {})
    context_names = _pick_context_names(context.get("cart", {})) + _pick_context_names(
        context.get("orders", {})
    )
    queries = _build_queries_from_text(
        state["user_message"],
        state["memory"],
        context_names,
    )
    return {"queries": queries}


async def _search_candidates_node(state: RecommendationState) -> RecommendationState:
    items: list[Candidate] = []
    context = state.get("context", {})
    context_names = _pick_context_names(context.get("cart", {})) + _pick_context_names(
        context.get("orders", {})
    )

    for query in state.get("queries", []):
        result = await _call_tool(
            state,
            "search_products",
            {
                "provider": "coupang",
                "keyword": query,
                "sort": "low_price"
                if state["memory"].price_preference == "lowest_price"
                else "relevance",
                "max_results": 5,
            },
        )
        for item in result.get("items", []) or []:
            items.append(_score_candidate(item, query, state["memory"], context_names))

    deduped: dict[str, Candidate] = {}
    for candidate in items:
        key = candidate.product_id or candidate.product_name
        previous = deduped.get(key)
        if previous is None or candidate.score > previous.score:
            deduped[key] = candidate

    ranked = sorted(deduped.values(), key=lambda candidate: candidate.score, reverse=True)
    return {"candidates": ranked[:5]}


async def _compare_prices_node(state: RecommendationState) -> RecommendationState:
    comparisons: dict[str, list[dict[str, Any]]] = {}

    for candidate in state.get("candidates", [])[:3]:
        offers = await compare_external_prices(
            candidate.source_query or candidate.product_name,
            candidate.product_name,
        )
        comparisons[candidate.product_id or candidate.product_name] = [
            {
                "source": offer.source,
                "title": offer.title,
                "price": offer.price,
                "price_text": offer.price_text,
                "url": offer.url,
            }
            for offer in offers[:3]
        ]

    return {"comparisons": comparisons}


async def _render_response_node(state: RecommendationState) -> RecommendationState:
    candidates = state.get("candidates", [])
    memory = state["memory"]
    context = state.get("context", {})
    comparisons = state.get("comparisons", {})

    if not candidates:
        issues = []
        for key in ("cart", "orders"):
            message = (context.get(key, {}) or {}).get("message")
            if message:
                issues.append(message)
        issue_text = " ".join(issues[:2]).strip()
        response = (
            "추천 후보를 아직 만들지 못했습니다. "
            "로그인 상태와 검색 가능 여부를 먼저 확인해주세요."
        )
        if issue_text:
            response = f"{response}\n\n현재 상태: {issue_text}"
        return {"response": response}

    lines = ["최근 대화와 주문/장바구니 흐름을 반영해서 골라봤어요."]
    if memory.preferred_categories:
        lines.append(f"기억 중인 선호 카테고리: {', '.join(memory.preferred_categories[:3])}")
    lines.append("")

    for index, candidate in enumerate(candidates[:3], start=1):
        compare_key = candidate.product_id or candidate.product_name
        external_offers = comparisons.get(compare_key, [])
        lines.append(
            f"{index}. {candidate.product_name} | {candidate.price or '가격 정보 없음'} | 평점 {candidate.rating or '-'}"
        )
        if candidate.reasons:
            lines.append(f"   이유: {', '.join(candidate.reasons)}")
        if candidate.product_link:
            lines.append(f"   링크: {candidate.product_link}")
        if external_offers:
            best_offer = min(external_offers, key=lambda offer: int(offer["price"]))
            lines.append(
                f"   외부 최저가: {best_offer['price_text']} ({best_offer['source']})"
            )
            if candidate.price:
                candidate_price = _price_to_number(candidate.price)
                if candidate_price is not None and int(best_offer["price"]) < candidate_price:
                    gap = candidate_price - int(best_offer["price"])
                    lines.append(f"   차이: 외부가가 약 {gap:,}원 더 저렴")
            lines.append(f"   비교 링크: {best_offer['url']}")

    if memory.price_preference == "lowest_price":
        lines.append("")
        lines.append("정렬은 쿠팡 검색 기준 저가 우선으로 맞췄습니다.")

    if not any(comparisons.values()):
        lines.append("외부 몰 가격 비교는 이번 요청에서 유효한 결과를 찾지 못해 쿠팡 기준으로만 정리했습니다.")
    return {"response": "\n".join(lines)}


async def run_recommendation_graph(
    *,
    user_message: str,
    memory: SessionMemory,
    tools: dict[str, BaseTool],
    on_tool: ToolEventHandler | None = None,
) -> tuple[str, list[str]]:
    graph = StateGraph(RecommendationState)
    graph.add_node("load_context", _load_context_node)
    graph.add_node("build_queries", _build_queries_node)
    graph.add_node("search_candidates", _search_candidates_node)
    graph.add_node("compare_prices", _compare_prices_node)
    graph.add_node("render_response", _render_response_node)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "build_queries")
    graph.add_edge("build_queries", "search_candidates")
    graph.add_edge("search_candidates", "compare_prices")
    graph.add_edge("compare_prices", "render_response")
    graph.add_edge("render_response", END)
    app = graph.compile()

    result = await app.ainvoke(
        {
            "user_message": user_message,
            "memory": memory,
            "tools": tools,
            "on_tool": on_tool,
        }
    )
    candidates = result.get("candidates", [])
    names = [candidate.product_name for candidate in candidates[:3]]
    return result.get("response", "추천 결과를 생성하지 못했습니다."), names
