from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ProductDetailImage",
    "ProductDetailProduct",
    "ProductDetailRequest",
    "ProductDetailResult",
    "ProductDetailSection",
    "ProductDetailTable",
    "ProductDetailTableRow",
    "ProductRating",
    "ProductRequiredInfo",
]


@dataclass(frozen=True, slots=True)
class ProductDetailRequest:
    url: str


@dataclass(frozen=True, slots=True)
class ProductRating:
    value: str
    count: str


@dataclass(frozen=True, slots=True)
class ProductDetailProduct:
    product_id: str
    item_id: str
    vendor_item_id: str
    url: str
    name: str
    brand: str
    description: str
    price: str
    currency: str
    availability: str
    rating: ProductRating
    breadcrumbs: tuple[str, ...]
    main_image_url: str


@dataclass(frozen=True, slots=True)
class ProductRequiredInfo:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class ProductDetailImage:
    url: str


@dataclass(frozen=True, slots=True)
class ProductDetailSection:
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class ProductDetailTableRow:
    cells: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductDetailTable:
    title: str
    headers: tuple[str, ...]
    rows: tuple[ProductDetailTableRow, ...]


@dataclass(frozen=True, slots=True)
class ProductDetailResult:
    success: bool
    provider: str
    message: str
    url: str
    product: ProductDetailProduct | None
    required_info: tuple[ProductRequiredInfo, ...]
    detail_images: tuple[ProductDetailImage, ...]
    sections: tuple[ProductDetailSection, ...]
    tables: tuple[ProductDetailTable, ...]
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()
