import json

from k_commerce_agent.profiles.kcommerce import attach_next_step


def test_status_logged_out_gets_ask_before_login_hint() -> None:
    raw = json.dumps({"provider": "coupang", "logged_in": False, "message": "로그인 안 됨"})

    result = json.loads(attach_next_step("status", raw))

    assert result["logged_in"] is False
    assert "login 도구를 바로 호출하지 마세요" in result["next_step"]


def test_status_logged_in_gets_proceed_hint() -> None:
    raw = json.dumps({"provider": "coupang", "logged_in": True, "message": "로그인됨"})

    result = json.loads(attach_next_step("status", raw))

    assert "바로 진행하세요" in result["next_step"]


def test_login_failure_gets_no_retry_hint() -> None:
    raw = json.dumps({"provider": "coupang", "success": False, "message": "로그인 실패"})

    result = json.loads(attach_next_step("login", raw))

    assert "다시 호출하지 말고" in result["next_step"]


def test_error_payload_gets_generic_no_retry_hint_for_any_tool() -> None:
    raw = json.dumps({"error": {"type": "tool_error", "message": "boom", "tool_name": "cart_clear"}})

    result = json.loads(attach_next_step("cart_clear", raw))

    assert result["error"]["message"] == "boom"
    assert "다시 호출하거나" in result["next_step"]


def test_list_tool_gets_card_display_hint() -> None:
    raw = json.dumps({"provider": "coupang", "success": True, "item_count": 2, "items": []})

    result = json.loads(attach_next_step("cart_list", raw))

    assert "화면 카드로 이미 표시되었습니다" in result["next_step"]
    assert "vendor_item_id" in result["next_step"]


def test_editable_review_list_hint_requires_delete_confirmation() -> None:
    raw = json.dumps({"provider": "coupang", "success": True, "items": []})

    result = json.loads(attach_next_step("review_list_editable", raw))

    assert "정말 삭제하시겠습니까" in result["next_step"]
    assert "review_id를 확인받거나 보여주지 마세요" in result["next_step"]


def test_web_search_gets_answer_from_results_hint() -> None:
    raw = json.dumps({"query": "q", "item_count": 1, "items": [{"index": 1, "title": "t"}]})

    result = json.loads(attach_next_step("web_search", raw))

    assert "화면에 표시되지 않습니다" in result["next_step"]


def test_review_action_failure_gets_no_unrelated_tools_hint() -> None:
    raw = json.dumps({"provider": "coupang", "success": False, "message": "수정 실패"})

    result = json.loads(attach_next_step("review_edit", raw))

    assert "관련 없는 도구를 호출하지 마세요" in result["next_step"]


def test_third_party_tool_with_colliding_name_is_left_untouched() -> None:
    """Another MCP server's ``status`` must not receive coupang guidance."""

    raw = json.dumps({"logged_in": False, "message": "vpn disconnected"})

    assert attach_next_step("status", raw, first_party=False) == raw


def test_third_party_tool_error_still_gets_no_retry_hint() -> None:
    raw = json.dumps({"error": {"type": "tool_error", "message": "boom", "tool_name": "fetch"}})

    result = json.loads(attach_next_step("fetch", raw, first_party=False))

    assert "다시 호출하거나" in result["next_step"]


def test_unknown_tool_success_payload_is_left_untouched() -> None:
    raw = json.dumps({"provider": "coupang", "success": True})

    assert attach_next_step("logout", raw) == raw


def test_non_json_content_is_left_untouched() -> None:
    assert attach_next_step("status", "plain text") == "plain text"


def test_content_block_list_gets_hint_in_text_blocks() -> None:
    raw = json.dumps({"provider": "coupang", "logged_in": True, "message": "로그인됨"})
    blocks = [{"type": "text", "text": raw}]

    result = attach_next_step("status", blocks)

    assert "next_step" in json.loads(result[0]["text"])
