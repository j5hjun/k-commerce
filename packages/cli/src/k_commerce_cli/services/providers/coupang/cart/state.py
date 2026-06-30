class CoupangCartState:
    SUCCESS = "success"
    NOT_LOGGED_IN = "not_logged_in"
    PAGE_LOAD_FAILED = "page_load_failed"
    ITEM_NOT_FOUND = "item_not_found"
    VALIDATION_ERROR = "validation_error"
    UPDATE_FAILED = "update_failed"
    BROWSER_CLOSED = "browser_closed"


CART_STATE_MESSAGES: dict[str, str] = {
    CoupangCartState.NOT_LOGGED_IN: "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
    CoupangCartState.PAGE_LOAD_FAILED: "쿠팡 장바구니 페이지를 불러오지 못했습니다.",
    CoupangCartState.ITEM_NOT_FOUND: "지정한 장바구니 상품을 찾을 수 없습니다.",
    CoupangCartState.VALIDATION_ERROR: "장바구니 입력값이 올바르지 않습니다.",
    CoupangCartState.UPDATE_FAILED: "장바구니 수량 수정에 실패했습니다.",
    CoupangCartState.BROWSER_CLOSED: "브라우저가 닫혀 장바구니 작업을 취소했습니다.",
}


def cart_state_message(state: str, *, fallback: str) -> str:
    return CART_STATE_MESSAGES.get(state, fallback)
