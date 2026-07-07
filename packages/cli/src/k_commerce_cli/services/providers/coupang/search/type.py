from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResultItem:
    index: int
    product_id: str
    product_name: str
    price: str
    rating: str
    image_url: str
    product_link: str


@dataclass(frozen=True)
class SearchProductResult:
    provider: str
    success: bool
    message: str
    items: tuple[SearchResultItem, ...]
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()
