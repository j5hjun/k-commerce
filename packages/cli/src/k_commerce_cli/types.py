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
