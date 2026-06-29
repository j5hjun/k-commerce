class CoupangReviewState:
    SUCCESS = "success"
    NOT_LOGGED_IN = "not_logged_in"
    ORDER_NOT_FOUND = "order_not_found"
    PRODUCT_NOT_FOUND = "product_not_found"
    ALREADY_REVIEWED = "already_reviewed"
    NOT_REVIEWABLE = "not_reviewable"
    SUBMIT_FAILED = "submit_failed"


REVIEW_STATE_MESSAGES: dict[str, str] = {
    CoupangReviewState.NOT_LOGGED_IN: "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
    CoupangReviewState.ORDER_NOT_FOUND: "지정한 주문을 찾을 수 없습니다.",
    CoupangReviewState.PRODUCT_NOT_FOUND: "지정한 상품을 찾을 수 없습니다.",
    CoupangReviewState.ALREADY_REVIEWED: "이미 리뷰가 작성된 상품입니다.",
    CoupangReviewState.NOT_REVIEWABLE: "리뷰를 작성할 수 없는 상품입니다.",
    CoupangReviewState.SUBMIT_FAILED: "리뷰 제출에 실패했습니다.",
}


def review_state_message(state: str, *, fallback: str) -> str:
    return REVIEW_STATE_MESSAGES.get(state, fallback)
