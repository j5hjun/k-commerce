from dataclasses import dataclass

from .provider import ProviderName


@dataclass(frozen=True)
class LoginResult:
    provider: ProviderName
    success: bool
    message: str
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class LogoutResult:
    provider: ProviderName
    success: bool
    message: str
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class StatusResult:
    provider: ProviderName
    logged_in: bool
    message: str
    error_code: str = ""
    retryable: bool = False
    next_tools: tuple[str, ...] = ()
