class CoupangCartState:
    SUCCESS = "success"
    NOT_LOGGED_IN = "not_logged_in"
    PAGE_LOAD_FAILED = "page_load_failed"


CART_STATE_MESSAGES: dict[str, str] = {
    CoupangCartState.NOT_LOGGED_IN: "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
    CoupangCartState.PAGE_LOAD_FAILED: "쿠팡 장바구니 페이지를 불러오지 못했습니다.",
}


def cart_state_message(state: str, *, fallback: str) -> str:
    return CART_STATE_MESSAGES.get(state, fallback)
