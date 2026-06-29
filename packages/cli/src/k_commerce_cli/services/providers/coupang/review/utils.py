from __future__ import annotations

from urllib.parse import urlencode

from .type import ReviewableItem

COUPANG_REVIEW_REGISTER_URL = "https://my.coupang.com/productreview/register"
PRODUCT_NAME_MAX_WIDTH = 50


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


def format_reviewable_list(items: tuple[ReviewableItem, ...]) -> str:
    """리뷰 작성 가능한 상품 목록을 CLI 출력용 표 형태로 만듭니다."""
    if not items:
        return "리뷰 작성 가능한 상품이 없습니다."

    lines = [
        f"리뷰 작성 가능 ({len(items)}건):",
        "",
        f"  {'#':>3}  {'배송일':<12}  {'상품ID':<12}  상품명",
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
