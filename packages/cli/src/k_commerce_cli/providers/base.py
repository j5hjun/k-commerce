from pathlib import Path
from typing import Protocol

from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult


class Terminal(Protocol):
    def echo(self, message: str) -> None: ...

    def info(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...


class Provider(Protocol):
    async def login(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LoginResult: ...

    async def status(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> StatusResult: ...

    async def logout(
        self,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> LogoutResult: ...
