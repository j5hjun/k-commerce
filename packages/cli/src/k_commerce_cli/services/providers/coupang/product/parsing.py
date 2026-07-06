from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qs, urlparse

from k_commerce_cli.services.types import (
    ProductDetailImage,
    ProductDetailProduct,
    ProductDetailSection,
    ProductDetailTable,
    ProductDetailTableRow,
    ProductRating,
    ProductRequiredInfo,
)

COUPANG_PRODUCT_PATH: Final = re.compile(r"^/vp/products/(?P<product_id>\d+)")


@dataclass(frozen=True, slots=True)
class ProductIdentifiers:
    product_id: str
    item_id: str
    vendor_item_id: str


@dataclass(frozen=True, slots=True)
class ProductBrowserResult:
    state: str
    product: ProductDetailProduct | None = None
    required_info: tuple[ProductRequiredInfo, ...] = ()
    detail_images: tuple[ProductDetailImage, ...] = ()
    sections: tuple[ProductDetailSection, ...] = ()
    tables: tuple[ProductDetailTable, ...] = ()
    message: str = ""


def parse_coupang_product_url(url: str) -> ProductIdentifiers | None:
    parsed = urlparse(url)
    if parsed.netloc not in {"www.coupang.com", "coupang.com"}:
        return None
    match = COUPANG_PRODUCT_PATH.match(parsed.path)
    if match is None:
        return None
    query = parse_qs(parsed.query)
    return ProductIdentifiers(
        product_id=match.group("product_id"),
        item_id=_first_query_value(query, "itemId"),
        vendor_item_id=_first_query_value(query, "vendorItemId"),
    )


def build_product_browser_result(raw: dict, identifiers: ProductIdentifiers, fallback_url: str) -> ProductBrowserResult:
    state = str(raw.get("state") or "success")
    if state != "success":
        return ProductBrowserResult(state=state, message=str(raw.get("message") or "상품 상세 수집에 실패했습니다."))

    product = _build_product(raw, identifiers, fallback_url)
    if product is None:
        return ProductBrowserResult(state="product_not_found", message="상품 정보를 찾지 못했습니다.")

    return ProductBrowserResult(
        state="success",
        product=product,
        required_info=_required_info(raw.get("requiredInfo")),
        detail_images=_detail_images(raw.get("detailImages")),
        sections=_sections(raw.get("sections")),
        tables=_tables(raw.get("tables")),
        message="상품 상세 정보를 수집했습니다.",
    )


def _first_query_value(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name, [])
    return values[0] if values else ""


def _build_product(raw: dict, identifiers: ProductIdentifiers, fallback_url: str) -> ProductDetailProduct | None:
    name = str(raw.get("name") or "").strip()
    canonical_url = str(raw.get("canonicalUrl") or fallback_url).strip()
    if not name:
        return None
    return ProductDetailProduct(
        product_id=str(raw.get("productId") or identifiers.product_id).strip(),
        item_id=str(raw.get("itemId") or identifiers.item_id).strip(),
        vendor_item_id=str(raw.get("vendorItemId") or identifiers.vendor_item_id).strip(),
        url=canonical_url,
        name=name,
        brand=str(raw.get("brand") or "").strip(),
        description=str(raw.get("description") or "").strip(),
        price=str(raw.get("price") or "").strip(),
        currency=str(raw.get("currency") or "").strip(),
        availability=str(raw.get("availability") or "").strip(),
        rating=ProductRating(
            value=str(raw.get("ratingValue") or "").strip(),
            count=str(raw.get("ratingCount") or "").strip(),
        ),
        breadcrumbs=_string_tuple(raw.get("breadcrumbs")),
        main_image_url=str(raw.get("mainImageUrl") or "").strip(),
    )


def _required_info(value) -> tuple[ProductRequiredInfo, ...]:
    if not isinstance(value, list):
        return ()
    items: list[ProductRequiredInfo] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label") or "").strip()
        item_value = str(entry.get("value") or "").strip()
        if label and item_value:
            items.append(ProductRequiredInfo(label=label, value=item_value))
    return tuple(items)


def _detail_images(value) -> tuple[ProductDetailImage, ...]:
    return tuple(ProductDetailImage(url=url) for url in _string_tuple(value))


def _sections(value) -> tuple[ProductDetailSection, ...]:
    if not isinstance(value, list):
        return ()
    sections: list[ProductDetailSection] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        text = str(entry.get("text") or "").strip()
        if title or text:
            sections.append(ProductDetailSection(title=title, text=text))
    return tuple(sections)


def _tables(value) -> tuple[ProductDetailTable, ...]:
    if not isinstance(value, list):
        return ()
    tables: list[ProductDetailTable] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        rows = entry.get("rows")
        if isinstance(rows, dict):
            rows = [rows]
        elif not isinstance(rows, list):
            rows = []
        tables.append(
            ProductDetailTable(
                title=str(entry.get("title") or "").strip(),
                headers=_string_tuple(entry.get("headers")),
                rows=tuple(ProductDetailTableRow(cells=_string_tuple(row)) for row in rows),
            )
        )
    return tuple(tables)


def _string_tuple(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, dict):
        items: list[str] = []
        for key, item in value.items():
            key_text = str(key or "").strip()
            item_text = str(item or "").strip()
            if key_text:
                items.append(key_text)
            if item_text:
                items.append(item_text)
        return tuple(items)
    if not isinstance(value, list):
        return ()
    items: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return tuple(items)
