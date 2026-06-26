from dataclasses import dataclass


@dataclass(frozen=True)
class LoginResult:
    provider: str
    success: bool
    message: str


@dataclass(frozen=True)
class LogoutResult:
    provider: str
    success: bool
    message: str


@dataclass(frozen=True)
class StatusResult:
    provider: str
    logged_in: bool
    message: str


@dataclass(frozen=True)
class OrderListEntry:
    title: str
    quantity: int
    status: str


@dataclass(frozen=True)
class OrderListResult:
    provider: str
    success: bool
    message: str
    orders: tuple[OrderListEntry, ...]
