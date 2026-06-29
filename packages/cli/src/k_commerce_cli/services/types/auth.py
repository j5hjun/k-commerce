from dataclasses import dataclass
from typing import Literal

ProviderName = Literal["coupang"]


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
