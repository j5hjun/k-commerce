class CoupangReviewState:
    SUCCESS = "success"
    BROWSER_CLOSED = "browser_closed"
    NOT_LOGGED_IN = "not_logged_in"
    ORDER_NOT_FOUND = "order_not_found"
    PRODUCT_NOT_FOUND = "product_not_found"
    REVIEW_NOT_FOUND = "review_not_found"
    IDENTIFIER_MISMATCH = "identifier_mismatch"
    ALREADY_REVIEWED = "already_reviewed"
    NOT_REVIEWABLE = "not_reviewable"
    NOT_EDITABLE = "not_editable"
    VALIDATION_ERROR = "validation_error"
    SUBMIT_FAILED = "submit_failed"


REVIEW_STATE_MESSAGES: dict[str, str] = {
    CoupangReviewState.BROWSER_CLOSED: "브라우저가 닫혀 작업을 계속할 수 없습니다.",
    CoupangReviewState.NOT_LOGGED_IN: "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
    CoupangReviewState.ORDER_NOT_FOUND: "지정한 주문을 찾을 수 없습니다.",
    CoupangReviewState.PRODUCT_NOT_FOUND: "지정한 상품을 찾을 수 없습니다.",
    CoupangReviewState.REVIEW_NOT_FOUND: "작성된 리뷰를 찾을 수 없습니다.",
    CoupangReviewState.IDENTIFIER_MISMATCH: "주문/상품/리뷰 식별자가 일치하지 않습니다.",
    CoupangReviewState.ALREADY_REVIEWED: "이미 리뷰가 작성된 상품입니다.",
    CoupangReviewState.NOT_REVIEWABLE: "리뷰를 작성할 수 없는 상품입니다.",
    CoupangReviewState.NOT_EDITABLE: "리뷰를 수정할 수 없는 상품입니다.",
    CoupangReviewState.VALIDATION_ERROR: "리뷰 입력값이 올바르지 않습니다.",
    CoupangReviewState.SUBMIT_FAILED: "리뷰 제출에 실패했습니다.",
}


def review_state_message(state: str, *, fallback: str) -> str:
    return REVIEW_STATE_MESSAGES.get(state, fallback)
