from dataclasses import dataclass

from .provider import ProviderName


@dataclass(frozen=True)
class LoginResult:
    provider: ProviderName
    success: bool
    message: str
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class LogoutResult:
    provider: ProviderName
    success: bool
    message: str
    next_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class StatusResult:
    provider: ProviderName
    logged_in: bool
    message: str
    next_tools: tuple[str, ...] = ()
