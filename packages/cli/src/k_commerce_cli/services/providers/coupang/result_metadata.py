from dataclasses import dataclass
from typing import Final

from nodriver.core.connection import ProtocolException
from websockets.exceptions import ConnectionClosed

from k_commerce_cli.services.providers.coupang.cart.state import CoupangCartState
from k_commerce_cli.services.providers.coupang.review.state import CoupangReviewState


@dataclass(frozen=True, slots=True)
class ResultMetadata:
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


EMPTY_METADATA: Final = ResultMetadata()
BROWSER_CLOSED_ERROR_CODE: Final = "browser_closed"
BROWSER_CLOSED_METADATA: Final = ResultMetadata(error_code=BROWSER_CLOSED_ERROR_CODE, retryable=True)
LOGIN_REQUIRED_METADATA: Final = ResultMetadata(
    error_code="not_logged_in",
    next_tools=("login",),
)
VALIDATION_METADATA: Final = ResultMetadata(error_code="validation_error")
BROWSER_CLOSED_ERROR_MARKERS: Final = (
    "browser closed",
    "connection closed",
    "session with given id not found",
    "target closed",
    "invalid target id",
    "no such target",
    "websocket connection is closed",
    "websocket is not connected",
)
BROWSER_CLOSED_EXCEPTIONS: Final = (RuntimeError, ConnectionError, ProtocolException, ConnectionClosed)

_CART_RETRYABLE_METADATA: Final[dict[str, ResultMetadata]] = {
    CoupangCartState.PAGE_LOAD_FAILED: ResultMetadata(error_code=CoupangCartState.PAGE_LOAD_FAILED, retryable=True),
    CoupangCartState.BROWSER_CLOSED: BROWSER_CLOSED_METADATA,
}

_REVIEW_RETRYABLE_METADATA: Final[dict[str, ResultMetadata]] = {
    CoupangReviewState.BROWSER_CLOSED: BROWSER_CLOSED_METADATA,
    CoupangReviewState.SUBMIT_FAILED: ResultMetadata(error_code=CoupangReviewState.SUBMIT_FAILED, retryable=True),
}

_CART_METADATA: Final[dict[str, ResultMetadata]] = {
    CoupangCartState.NOT_LOGGED_IN: LOGIN_REQUIRED_METADATA,
    CoupangCartState.ITEM_NOT_FOUND: ResultMetadata(
        error_code=CoupangCartState.ITEM_NOT_FOUND,
        next_tools=("cart_list",),
    ),
    CoupangCartState.VALIDATION_ERROR: VALIDATION_METADATA,
    CoupangCartState.UPDATE_FAILED: ResultMetadata(error_code=CoupangCartState.UPDATE_FAILED, retryable=True),
    CoupangCartState.DELETE_FAILED: ResultMetadata(error_code=CoupangCartState.DELETE_FAILED, retryable=True),
    **_CART_RETRYABLE_METADATA,
}

_REVIEW_METADATA: Final[dict[str, ResultMetadata]] = {
    CoupangReviewState.NOT_LOGGED_IN: LOGIN_REQUIRED_METADATA,
    CoupangReviewState.ORDER_NOT_FOUND: ResultMetadata(
        error_code=CoupangReviewState.ORDER_NOT_FOUND,
        next_tools=("review_list_reviewable", "order_list"),
    ),
    CoupangReviewState.PRODUCT_NOT_FOUND: ResultMetadata(
        error_code=CoupangReviewState.PRODUCT_NOT_FOUND,
        next_tools=("review_list_reviewable", "order_list"),
    ),
    CoupangReviewState.REVIEW_NOT_FOUND: ResultMetadata(
        error_code=CoupangReviewState.REVIEW_NOT_FOUND,
        next_tools=("review_list_editable",),
    ),
    CoupangReviewState.IDENTIFIER_MISMATCH: ResultMetadata(
        error_code=CoupangReviewState.IDENTIFIER_MISMATCH,
        next_tools=("review_list_reviewable", "review_list_editable"),
    ),
    CoupangReviewState.ALREADY_REVIEWED: ResultMetadata(
        error_code=CoupangReviewState.ALREADY_REVIEWED,
        next_tools=("review_list_editable",),
    ),
    CoupangReviewState.NOT_REVIEWABLE: ResultMetadata(
        error_code=CoupangReviewState.NOT_REVIEWABLE,
        next_tools=("review_list_reviewable",),
    ),
    CoupangReviewState.NOT_EDITABLE: ResultMetadata(
        error_code=CoupangReviewState.NOT_EDITABLE,
        next_tools=("review_list_editable",),
    ),
    CoupangReviewState.VALIDATION_ERROR: VALIDATION_METADATA,
    **_REVIEW_RETRYABLE_METADATA,
}

_SEARCH_METADATA: Final[dict[str, ResultMetadata]] = {
    "not_logged_in": LOGIN_REQUIRED_METADATA,
    "no_results": ResultMetadata(error_code="no_results"),
    BROWSER_CLOSED_ERROR_CODE: BROWSER_CLOSED_METADATA,
}


def cart_metadata(state: str) -> ResultMetadata:
    return _CART_METADATA.get(state, ResultMetadata(error_code=state, retryable=True))


def review_metadata(state: str) -> ResultMetadata:
    return _REVIEW_METADATA.get(state, ResultMetadata(error_code=state, retryable=True))


def search_metadata(state: str) -> ResultMetadata:
    return _SEARCH_METADATA.get(state, ResultMetadata(error_code=state, retryable=True))


def is_browser_closed_error(error: Exception) -> bool:
    if isinstance(error, ConnectionClosed):
        return True
    message = str(error).lower()
    return any(marker in message for marker in BROWSER_CLOSED_ERROR_MARKERS)
