from pathlib import Path
from typing import Protocol

from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult


class AuthProvider(Protocol):
    name: str

    async def login(self, root_dir: Path | None = None) -> LoginResult: ...

    async def status(self, root_dir: Path | None = None) -> StatusResult: ...

    async def logout(self, root_dir: Path | None = None) -> LogoutResult: ...
