from pathlib import Path
from typing import Protocol

from k_commerce_cli.types import (
    LoginResult,
    LogoutResult,
    OrderListResult,
    StatusResult,
)


class AuthProvider(Protocol):
    async def login(self, root_dir: Path | None = None) -> LoginResult: ...

    async def status(self, root_dir: Path | None = None) -> StatusResult: ...

    async def logout(self, root_dir: Path | None = None) -> LogoutResult: ...


class OrderProvider(Protocol):
    async def list_orders(self, root_dir: Path | None = None) -> OrderListResult: ...
