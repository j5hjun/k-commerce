from typing import Protocol

from k_commerce_cli.types import LoginResult


class LoginProvider(Protocol):
    name: str

    async def login(self) -> LoginResult:
        ...
