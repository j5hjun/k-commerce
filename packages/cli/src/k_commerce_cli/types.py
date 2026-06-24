from dataclasses import dataclass


@dataclass(frozen=True)
class LoginResult:
    provider: str
    success: bool
    message: str
