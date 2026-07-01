from urllib.parse import urlencode

from k_commerce_cli.services.types import EditableReviewItem, ReviewableItem

COUPANG_REVIEW_REGISTER_URL = "https://my.coupang.com/productreview/register"
COUPANG_WROTE_REVIEWS_URL = "https://my.coupang.com/productreview/wroteReviews"
PRODUCT_NAME_MAX_WIDTH = 50
REVIEW_TEXT_MAX_WIDTH = 30


def format_rating(rating: int) -> str:
    if not 1 <= rating <= 5:
        return "-"
    return f"{'★' * rating}{'☆' * (5 - rating)}"


def build_review_register_url(
    *,
    completed_order_vendor_item_id: str,
    product_id: str,
    delivery_date: str,
    vendor_item_id: str,
) -> str:
    """리뷰 작성 가능한 주문 상품의 쿠팡 리뷰 등록 URL을 만듭니다."""
    query = urlencode(
        {
            "completedOrderVendorItemId": completed_order_vendor_item_id,
            "productId": product_id,
            "deliveryDate": delivery_date,
            "vendorItemId": vendor_item_id,
        }
    )
    return f"{COUPANG_REVIEW_REGISTER_URL}?{query}"


def build_review_modify_url(*, review_id: str, page: int = 1) -> str:
    """작성한 리뷰의 쿠팡 리뷰 수정 URL을 만듭니다."""
    query = urlencode({"page": page})
    return f"{COUPANG_WROTE_REVIEWS_URL}/{review_id}/modify?{query}"


def format_reviewable_list(items: tuple[ReviewableItem, ...]) -> str:
    """리뷰 작성 가능한 상품 목록을 CLI 출력용 표 형태로 만듭니다."""
    if not items:
        return "리뷰 작성 가능한 상품이 없습니다."

    lines = [
        f"리뷰 작성 가능 ({len(items)}건):",
        "",
        f"  {'No':>3}  {'배송일':<12}  {'상품ID':<12}  상품명",
    ]
    for item in items:
        product_name = (
            item.product_name
            if len(item.product_name) <= PRODUCT_NAME_MAX_WIDTH
            else f"{item.product_name[: PRODUCT_NAME_MAX_WIDTH - 3]}..."
        )
        lines.append(
            f"  {item.index:>3}  {item.delivery_date:<12}  {item.product_id:<12}  {product_name}"
        )
    return "\n".join(lines)


def format_editable_review_list(items: tuple[EditableReviewItem, ...]) -> str:
    """수정 가능한 작성 리뷰 목록을 CLI 출력용 표 형태로 만듭니다."""
    return _format_written_review_list(
        items,
        list_label="리뷰 수정 가능",
        empty_message="수정 가능한 작성 리뷰가 없습니다.",
    )


def format_deletable_review_list(items: tuple[EditableReviewItem, ...]) -> str:
    """삭제 가능한 작성 리뷰 목록을 CLI 출력용 표 형태로 만듭니다."""
    return _format_written_review_list(
        items,
        list_label="리뷰 삭제 가능",
        empty_message="삭제 가능한 작성 리뷰가 없습니다.",
        show_review_id=False,
    )


def _format_written_review_list(
    items: tuple[EditableReviewItem, ...],
    *,
    list_label: str,
    empty_message: str,
    show_review_id: bool = True,
) -> str:
    if not items:
        return empty_message

    if show_review_id:
        header = f"  {'No':>3}  {'평점':<7}  {'리뷰ID':<12}  {'상품ID':<12}  상품명 / 후기"
    else:
        header = f"  {'No':>3}  {'상품ID':<12}  {'평점':<7}  상품명 / 후기"

    lines = [
        f"{list_label} ({len(items)}건):",
        "",
        header,
    ]
    for item in items:
        product_name = (
            item.product_name
            if len(item.product_name) <= PRODUCT_NAME_MAX_WIDTH
            else f"{item.product_name[: PRODUCT_NAME_MAX_WIDTH - 3]}..."
        )
        review_text = (
            item.review_text
            if len(item.review_text) <= REVIEW_TEXT_MAX_WIDTH
            else f"{item.review_text[: REVIEW_TEXT_MAX_WIDTH - 3]}..."
        )
        suffix = f" / {review_text}" if review_text else ""
        if show_review_id:
            lines.append(
                f"  {item.index:>3}  {format_rating(item.rating):<7}  {item.review_id:<12}  {item.product_id:<12}  {product_name}{suffix}"
            )
        else:
            lines.append(
                f"  {item.index:>3}  {item.product_id:<12}  {format_rating(item.rating):<7}  {product_name}{suffix}"
            )
    return "\n".join(lines)
