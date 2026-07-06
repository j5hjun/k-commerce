from dataclasses import dataclass

from k_commerce_cli.services.types.provider import ProviderName


@dataclass(frozen=True)
class ReviewUploadRequest:
    order_id: str
    product_id: str
    rating: int
    text: str
    review_url: str


@dataclass(frozen=True)
class ReviewUploadResult:
    provider: ProviderName
    success: bool
    message: str
    order_id: str
    product_id: str
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewEditRequest:
    order_id: str
    product_id: str
    review_id: str
    rating: int
    text: str


@dataclass(frozen=True)
class ReviewEditResult:
    provider: ProviderName
    success: bool
    message: str
    order_id: str
    product_id: str
    review_id: str
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewDeleteRequest:
    review_id: str
    product_id: str = ""
    order_id: str = ""


@dataclass(frozen=True)
class ReviewDeleteResult:
    provider: ProviderName
    success: bool
    message: str
    review_id: str
    product_id: str = ""
    order_id: str = ""
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class EditableReviewItem:
    index: int
    review_id: str
    product_id: str
    order_id: str
    product_name: str
    rating: int
    review_text: str
    modify_url: str


@dataclass(frozen=True)
class ListEditableReviewsResult:
    provider: ProviderName
    success: bool
    message: str
    items: tuple[EditableReviewItem, ...]
    next_tools: tuple[str, ...] = ()


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
    provider: ProviderName
    success: bool
    message: str
    items: tuple[ReviewableItem, ...]
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ReviewableItemData:
    product_id: str
    product_name: str
    delivery_date: str
    completed_order_vendor_item_id: str
    vendor_item_id: str
    review_url: str


@dataclass(frozen=True)
class _EditableReviewItemData:
    review_id: str
    product_id: str
    order_id: str
    product_name: str
    rating: int
    review_text: str
    modify_url: str


@dataclass(frozen=True)
class _ListReviewableBrowserResult:
    state: str
    items: tuple[_ReviewableItemData | _EditableReviewItemData, ...] = ()
    message: str | None = None


@dataclass(frozen=True)
class _ReviewUploadBrowserResult:
    state: str
    message: str | None = None
