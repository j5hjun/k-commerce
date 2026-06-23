from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LoginResult:
    provider: str
    success: bool
    message: str


class LoginProvider(Protocol):
    name: str

    def login(self) -> LoginResult:
        ...