from dataclasses import dataclass
from typing import Literal

from k_commerce_cli.providers.constants import ProviderName

OrderStatus = Literal[
    "결제완료",
    "상품준비중",
    "배송중",
    "배송완료",
    "취소",
    "반품",
    "교환",
    "배송시작",
]


@dataclass(frozen=True)
class LoginResult:
    provider: ProviderName
    success: bool
    message: str


@dataclass(frozen=True)
class LogoutResult:
    provider: ProviderName
    success: bool
    message: str


@dataclass(frozen=True)
class StatusResult:
    provider: ProviderName
    logged_in: bool
    message: str


@dataclass(frozen=True)
class OrderListEntry:
    order_date: str
    title: str
    quantity: int
    status: OrderStatus
    product_url: str = ""


@dataclass(frozen=True)
class OrderListResult:
    provider: ProviderName
    success: bool
    message: str
    orders: tuple[OrderListEntry, ...]


@dataclass(frozen=True)
class LoginPageState:
    url: str
    has_login_link: bool
    has_mycoupang_link: bool


@dataclass(frozen=True)
class OrderPageState:
    url: str
    ready: bool
    has_login_prompt: bool
    has_order_signals: bool
    has_empty_state: bool
    has_loading_indicator: bool
