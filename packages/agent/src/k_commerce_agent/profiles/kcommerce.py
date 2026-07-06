"""k-commerce first-party profile.

Everything in this module is specific to the bundled k-commerce MCP server and
this app's web UI (card display contract, coupang flows). The rest of the
agent package is a generic MCP host: it must work unchanged with any
registered third-party MCP server, so k-commerce specifics live here only.
"""

import json
from typing import Any

SYSTEM_PROMPT = (
    "당신은 한국 커머스 자동화를 돕는 어시스턴트입니다. 사용자에게는 한국어로 간결하게 답하세요. "
    "커머스 작업(로그인 상태, 주문, 장바구니, 상품 검색, 리뷰)에는 반드시 MCP 도구를 사용하세요. "
    "web_search는 MCP 도구로 답할 수 없는 외부 정보(뉴스, 비교 기사, 영양 성분 등)가 필요할 때만 "
    "fallback으로 사용하고, 로그인 상태나 쿠팡 계정 관련 질문에는 쓰지 마세요. "
    "도구의 provider 인자는 항상 소문자 식별자를 사용하고(예: 'coupang'), "
    "특별한 언급이 없으면 'coupang'으로 간주하세요. "
    "사용자가 로그인 상태만 묻는 경우 status 도구만 호출하세요. "
    "주문 조회, 장바구니, 리뷰처럼 로그인이 필요한 작업 전에는 반드시 먼저 status 도구로 "
    "로그인 상태를 확인하세요. "
    "대화 기록에 이미 필요한 도구 결과가 있으면 같은 도구를 다시 호출하지 말고 그 결과를 사용하세요. "
    "여러 도구를 순서대로 호출해야 하는 경우, 각 도구의 결과를 확인한 뒤 다음 도구를 호출하세요. "
    "도구 결과의 next_step 필드는 다음 행동 지침입니다. 반드시 그대로 따르세요. "
    "review_delete는 사용자가 삭제에 명확히 동의하기 전에는 절대 호출하지 마세요."
)

# Post-result guidance attached per tool result as a ``next_step`` field.
# Keeping the guidance next to the result it applies to is far more reliable
# for mid-size models than rules buried in a long system prompt.

_STATUS_LOGGED_IN = (
    "이미 로그인되어 있습니다. login이나 status를 다시 호출하지 말고 요청받은 작업을 바로 진행하세요."
)
_STATUS_LOGGED_OUT = (
    "login 도구를 바로 호출하지 마세요. 현재 로그인되어 있지 않다고 알리고 "
    "'로그인하시겠습니까?'라고 물어본 뒤, 사용자가 동의한 경우에만 login을 호출하세요."
)
_LOGIN_SUCCESS = (
    "로그인에 성공했습니다. status를 다시 호출하지 말고 사용자가 원래 요청한 작업을 이어서 진행하세요."
)
_LOGIN_FAILURE = (
    "로그인에 실패했습니다. 같은 턴에서 login을 다시 호출하지 말고, "
    "실패를 간단히 알린 뒤 잠시 후 다시 시도하도록 안내하세요."
)

_TOOL_ERROR = (
    "도구 실행이 실패했습니다. 같은 턴에서 이 도구를 다시 호출하거나 "
    "관련 없는 다른 도구를 호출하지 마세요. 실패를 간단히 알린 뒤 "
    "잠시 후 다시 시도하도록 안내하세요."
)

# Every list tool shares the same display contract with the web UI: the
# result is rendered as a card, so the assistant must not repeat it.
_LIST_COMMON = (
    "이 목록은 화면 카드로 이미 표시되었습니다. 목록·번호·상품명을 assistant 응답에 "
    "다시 나열하지 말고, 카드에 없는 추가 질문이 필요할 때만 한두 문장으로 말하세요. "
    "사용자가 'N번', '첫 번째'처럼 번호로 항목을 지칭하면 이 결과의 index N 항목을 사용하세요. "
    "사용자가 '더 보여줘', '계속', '다음', '나머지'를 요청해도 이 도구를 다시 호출하지 말고, "
    "결과의 개수 필드(total_count·shown_count 또는 item_count)를 확인해 "
    "아직 보여주지 않은 항목만 간단히 안내하세요. "
    "'새로고침', '다시 조회'처럼 최신 데이터를 명시적으로 요청할 때만 재조회하세요."
)

_LIST_SPECIFIC: dict[str, str] = {
    "order_list": (
        "사용자가 '5개만', '상위 10건'처럼 개수를 지정하면 그 개수만 참고하세요."
    ),
    "cart_list": (
        "장바구니 항목을 변경·삭제할 때는 이 결과의 product_id, vendor_item_id, item_id를 "
        "그대로 사용하세요."
    ),
    "search_products": (
        "상품 상세·후속 작업에는 이 결과의 product_id를 우선 사용하고, "
        "부족한 정보만 web_search로 보완하세요."
    ),
    "review_list_reviewable": (
        "사용자가 번호를 고르면 그 항목으로 review_upload(신규 리뷰 작성)를 진행하세요. "
        "review_upload의 order_id에는 해당 항목의 completed_order_vendor_item_id를 넣고, "
        "product_id는 JSON에 있으면 함께 넣으세요. "
        "평점(1~5)이나 리뷰 본문이 아직 없으면 사용자에게 물어본 뒤 호출하세요."
    ),
    "review_list_editable": (
        "사용자가 번호를 고르면 review_edit(수정) 또는 review_delete(삭제)를 진행하세요. "
        "review_id는 이 결과 JSON에서 해당 index 항목의 값을 찾아 넣고, "
        "사용자에게 review_id를 확인받거나 보여주지 마세요. "
        "삭제 요청이면 review_delete를 바로 호출하지 말고, 상품명과 가능하면 평점·리뷰 일부를 "
        "보여주며 복구할 수 없다는 점을 안내한 뒤 '정말 삭제하시겠습니까?'라고 물어보고, "
        "사용자가 명확히 동의한 뒤에만 호출하세요. "
        "수정 요청이면 평점·본문이 없을 때만 물어보고 review_edit를 진행하세요."
    ),
}

_WEB_SEARCH = (
    "이 검색 결과는 사용자 화면에 표시되지 않습니다. 반드시 결과 내용을 바탕으로 "
    "사용자 질문에 답하는 assistant 응답을 작성하세요. 응답을 비우거나 "
    "URL·제목 목록을 그대로 나열하지 마세요."
)

_REVIEW_ACTION_SUCCESS = (
    "작업이 완료되었고 결과는 화면 카드로 표시됩니다. 한 문장으로만 간단히 알리세요."
)
_REVIEW_ACTION_FAILURE = (
    "작업이 실패했습니다. order_list, cart_list, status 등 관련 없는 도구를 호출하지 마세요. "
    "실패 이유를 간단히 알리고 같은 작업을 다시 시도하도록 안내하세요."
)

_REVIEW_ACTION_TOOLS = frozenset({"review_upload", "review_edit", "review_delete"})


def _next_step_for(tool_name: str, payload: dict[str, Any], first_party: bool) -> str | None:
    # Error payloads come from this host's error wrapper, so the no-retry
    # guidance applies to every tool regardless of which server it came from.
    if "error" in payload:
        return _TOOL_ERROR
    if not first_party:
        return None
    if tool_name == "status":
        logged_in = payload.get("logged_in")
        if isinstance(logged_in, bool):
            return _STATUS_LOGGED_IN if logged_in else _STATUS_LOGGED_OUT
        return None
    if tool_name == "login":
        success = payload.get("success")
        if isinstance(success, bool):
            return _LOGIN_SUCCESS if success else _LOGIN_FAILURE
        return None
    if tool_name in _LIST_SPECIFIC:
        return f"{_LIST_COMMON} {_LIST_SPECIFIC[tool_name]}"
    if tool_name == "web_search":
        return _WEB_SEARCH
    if tool_name in _REVIEW_ACTION_TOOLS:
        success = payload.get("success")
        if isinstance(success, bool):
            return _REVIEW_ACTION_SUCCESS if success else _REVIEW_ACTION_FAILURE
        return None
    return None


def _inject_next_step(tool_name: str, raw: str, first_party: bool) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(parsed, dict):
        return raw
    next_step = _next_step_for(tool_name, parsed, first_party)
    if next_step is None:
        return raw
    return json.dumps({**parsed, "next_step": next_step}, ensure_ascii=False)


def attach_next_step(tool_name: str, content: Any, *, first_party: bool = True) -> Any:
    """Append a next-step hint to tool results before the LLM sees them.

    Tool-name-keyed guidance only fires for first-party tools (the bundled
    k-commerce server and this package's own tools) so a third-party MCP tool
    that happens to share a name (e.g. another server's ``status``) passes
    through untouched. Error payloads get the generic no-retry hint for every
    tool, since this host produced them.
    """

    if isinstance(content, str):
        return _inject_next_step(tool_name, content, first_party)
    if isinstance(content, list):
        blocks: list[Any] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    blocks.append({**block, "text": _inject_next_step(tool_name, text, first_party)})
                    continue
            blocks.append(block)
        return blocks
    return content
