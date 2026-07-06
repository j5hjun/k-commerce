from dataclasses import dataclass


@dataclass(frozen=True)
class CartItem:
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
    image_url: str = ""
    product_link: str = ""


@dataclass(frozen=True)
class ListCartResult:
    provider: str
    success: bool
    message: str
    items: tuple[CartItem, ...]


@dataclass(frozen=True)
class CartDeleteRequest:
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""


@dataclass(frozen=True)
class CartDeleteResult:
    provider: str
    success: bool
    message: str
    deleted_count: int = 0


@dataclass(frozen=True)
class CartQuantityUpdateRequest:
    quantity: int
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""


@dataclass(frozen=True)
class CartQuantityUpdateResult:
    provider: str
    success: bool
    message: str
    quantity: int
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""
    product_name: str = ""
    option_text: str = ""
    notice: str = ""


@dataclass(frozen=True)
class _CartItemData:
    product_name: str
    option_text: str
    quantity: int
    unit_price: str
    total_price: str
    product_id: str = ""
    vendor_item_id: str = ""
    item_id: str = ""
    delivery_text: str = ""
    image_url: str = ""
    product_link: str = ""


@dataclass(frozen=True)
class _ListCartBrowserResult:
    state: str
    items: tuple[_CartItemData, ...] = ()
    message: str | None = None
    applied_quantity: int | None = None
    product_name: str = ""
    option_text: str = ""
