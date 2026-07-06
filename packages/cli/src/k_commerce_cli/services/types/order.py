from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from k_commerce_cli.services.providers.coupang.types import CoupangOrderList

__all__ = [
    "OrderDetailItem",
    "OrderDetailRequest",
    "OrderDetailResult",
    "OrderFailureItem",
    "OrderFailuresRequest",
    "OrderFailuresResult",
    "OrderListItem",
    "OrderListRequest",
    "OrderListResult",
    "OrderResult",
    "OrderSyncRequest",
    "OrderSyncResult",
]


@dataclass(frozen=True, slots=True)
class OrderSyncRequest:
    start_date: str | None = None
    end_date: str | None = None
    failed_only: bool = False
    refresh: bool = False


@dataclass(frozen=True, slots=True)
class OrderListRequest:
    start_date: str | None = None
    end_date: str | None = None
    status: str = "all"
    limit: int = 50
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class OrderDetailRequest:
    order_id: str


@dataclass(frozen=True, slots=True)
class OrderFailuresRequest:
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class OrderListItem:
    order_id: str
    ordered_at: str
    status: str
    title: str
    amount: int


@dataclass(frozen=True, slots=True)
class OrderFailureItem:
    order_id: str
    ordered_at: str
    failure_type: str
    title: str


@dataclass(frozen=True, slots=True)
class OrderDetailItem:
    vendor_item_id: str
    name: str
    quantity: int
    amount: int


@dataclass(frozen=True, slots=True)
class OrderSyncResult:
    success: bool
    provider: str
    message: str
    start_date: str | None = None
    end_date: str | None = None
    collected_orders: int = 0
    total_orders: int = 0
    payload: CoupangOrderList | None = None
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OrderListResult:
    success: bool
    provider: str
    message: str
    start_date: str | None
    end_date: str | None
    count: int
    total_count: int
    has_more: bool
    next_cursor: str | None
    orders: tuple[OrderListItem, ...]
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OrderDetailResult:
    success: bool
    provider: str
    message: str
    order_id: str
    ordered_at: str = ""
    status: str = ""
    title: str = ""
    amount: int = 0
    items: tuple[OrderDetailItem, ...] = ()
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OrderFailuresResult:
    success: bool
    provider: str
    message: str
    start_date: str | None
    end_date: str | None
    count: int
    orders: tuple[OrderFailureItem, ...]
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


OrderResult: TypeAlias = OrderSyncResult | OrderListResult | OrderDetailResult | OrderFailuresResult
