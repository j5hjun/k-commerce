from __future__ import annotations

from pydantic import BaseModel


class MemorySummaryResponse(BaseModel):
    session_id: str
    preferred_categories: list[str]
    avoided_keywords: list[str]
    recent_queries: list[str]
    recent_recommendations: list[str]
    price_preference: str | None = None
    delivery_preference: str | None = None
    last_intent: str


class OrderProductResponse(BaseModel):
    product: str
    price: str
    quantity: int
    link: str | None = None
    image: str | None = None


class OrderGroupResponse(BaseModel):
    id: str
    order_id: str
    shipment_box_id: str | None = None
    status: str
    raw_status: str
    display_status: str | None = None
    invoice_number: str | None = None
    delivery_message: str | None = None
    has_track_action: bool = False
    has_exchange_return_action: bool = False
    has_write_review_action: bool = False
    date: str
    ordered_at: int
    year: str
    items: list[OrderProductResponse]


class OrdersResponse(BaseModel):
    total: int
    collected_at: str | None = None
    years: list[str] = []
    groups: list[OrderGroupResponse]


class ProviderLoginStatusResponse(BaseModel):
    provider: str
    logged_in: bool
    message: str


class ProviderLoginResponse(BaseModel):
    provider: str
    success: bool
    message: str


class CartItemResponse(BaseModel):
    index: int
    product_name: str
    option_text: str
    quantity: int
    unit_price: str
    total_price: str
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""
    delivery_text: str = ""


class CartListResponse(BaseModel):
    provider: str
    success: bool
    message: str
    items: list[CartItemResponse] = []


class ProductSearchItemResponse(BaseModel):
    index: int
    product_id: str
    product_name: str
    price: str
    rating: str
    image_url: str
    product_link: str


class ProductSearchResponse(BaseModel):
    provider: str
    success: bool
    message: str
    items: list[ProductSearchItemResponse] = []


class CartItemIdentityBody(BaseModel):
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""


class CartQuantityUpdateBody(CartItemIdentityBody):
    provider: str = "coupang"
    quantity: int


class CartDeleteBody(CartItemIdentityBody):
    provider: str = "coupang"


class CartBulkDeleteBody(BaseModel):
    provider: str = "coupang"
    items: list[CartItemIdentityBody]


class CartMutationResponse(BaseModel):
    provider: str
    success: bool
    message: str
    deleted_count: int = 0
    quantity: int | None = None
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""
    notice: str = ""


class DeliveryTrackingEventResponse(BaseModel):
    time: str | None = None
    status: str
    description: str | None = None
    location: str | None = None


class DeliveryTrackingResponse(BaseModel):
    provider: str
    order_id: str
    shipment_box_id: str
    invoice_number: str | None = None
    display_status: str | None = None
    courier_name: str | None = None
    tracking_number: str | None = None
    summary: str | None = None
    raw_lines: list[str] = []
    collected_at: str | None = None
    events: list[DeliveryTrackingEventResponse] = []


class ReviewableItemResponse(BaseModel):
    index: int
    product_id: str
    product_name: str
    delivery_date: str
    completed_order_vendor_item_id: str
    vendor_item_id: str
    review_url: str


class EditableReviewItemResponse(BaseModel):
    index: int
    review_id: str
    product_id: str
    order_id: str
    product_name: str
    rating: int
    review_text: str
    modify_url: str


class ReviewableListResponse(BaseModel):
    provider: str
    success: bool
    message: str
    items: list[ReviewableItemResponse] = []


class EditableReviewListResponse(BaseModel):
    provider: str
    success: bool
    message: str
    items: list[EditableReviewItemResponse] = []


class ReviewListResponse(BaseModel):
    provider: str
    success: bool
    message: str
    reviewable: ReviewableListResponse
    editable: EditableReviewListResponse


class ReviewUploadRequestBody(BaseModel):
    provider: str = "coupang"
    order_id: str
    product_id: str
    rating: int
    text: str
    review_url: str


class ReviewEditRequestBody(BaseModel):
    provider: str = "coupang"
    order_id: str
    product_id: str
    rating: int
    text: str


class ReviewDeleteRequestBody(BaseModel):
    provider: str = "coupang"
    product_id: str = ""
    order_id: str = ""


class ReviewMutationResponse(BaseModel):
    provider: str
    success: bool
    message: str
    review_id: str | None = None
    product_id: str | None = None
    order_id: str | None = None
