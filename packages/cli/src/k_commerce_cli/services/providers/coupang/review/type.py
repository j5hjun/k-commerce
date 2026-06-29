from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewUploadRequest:
    order_id: str
    product_id: str
    rating: int
    text: str
    review_url: str


@dataclass(frozen=True)
class ReviewUploadResult:
    provider: str
    success: bool
    message: str
    order_id: str
    product_id: str


@dataclass(frozen=True)
class ReviewableItem:
    index: int
    product_id: str
    product_name: str
    delivery_date: str
    completed_order_vendor_item_id: str
    vendor_item_id: str
    review_url: str


@dataclass(frozen=True)
class ListReviewableResult:
    provider: str
    success: bool
    message: str
    items: tuple[ReviewableItem, ...]
