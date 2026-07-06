from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from k_commerce_cli.services.providers.coupang.types import CoupangOrderList

__all__ = [
    "OrderDetailRequest",
    "OrderDetailResult",
    "OrderFailuresRequest",
    "OrderFailuresResult",
    "OrderListRequest",
    "OrderListResult",
    "OrderResult",
    "OrderSearchRequest",
    "OrderSearchResult",
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
class OrderSearchRequest:
    keyword: str
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class OrderFailuresRequest:
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class OrderSyncResult:
    success: bool
    provider: str
    message: str
    start_date: str | None = None
    end_date: str | None = None
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
    total_count: int
    has_more: bool
    next_cursor: str | None
    payload: CoupangOrderList | None = None
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OrderSearchResult:
    success: bool
    provider: str
    message: str
    keyword: str
    start_date: str | None
    end_date: str | None
    total_count: int
    payload: CoupangOrderList | None = None
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OrderDetailResult:
    success: bool
    provider: str
    message: str
    order_id: str
    payload: CoupangOrderList | None = None
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
    payload: CoupangOrderList | None = None
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


OrderResult: TypeAlias = OrderSyncResult | OrderListResult | OrderSearchResult | OrderDetailResult | OrderFailuresResult
