from pathlib import Path
from typing import Protocol

from k_commerce_cli.types import LoginResult, LogoutResult


class LoginProvider(Protocol):
    name: str

    async def login(self, root_dir: Path | None = None) -> LoginResult:
        ...


class LogoutProvider(Protocol):
    name: str

    async def logout(self, root_dir: Path | None = None) -> LogoutResult:
        ...
