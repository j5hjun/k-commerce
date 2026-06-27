from pathlib import Path
from typing import Protocol

from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult
from k_commerce_cli.base import Terminal

class BrowserElement(Protocol):
    text_all: str
    children: list["BrowserElement"]

    async def query_selector_all(self, selector: str) -> list["BrowserElement"]: ...

    async def click(self) -> None: ...

    async def send_keys(self, text: str) -> None: ...


class BrowserTab(Protocol):
    url: str

    async def get(self, url: str) -> None: ...

    async def select(self, selector: str, timeout: int = 0) -> BrowserElement | None: ...


class BrowserSession(Protocol):
    tab: BrowserTab


class Browser(Protocol):
    async def launch(self, paths: ProviderPaths) -> BrowserSession: ...

    async def save_session(self, session: BrowserSession, cookies_file: Path) -> None: ...

    async def close(self, session: BrowserSession) -> None: ...

    async def select(
        self,
        tab: BrowserTab,
        selector: str,
        timeout: int = 1,
    ) -> BrowserElement | None: ...


class Store(Protocol):
    paths: ProviderPaths
    base_dir: Path
    profile_dir: Path
    cookies_file: Path
    credentials_path: Path
    session_meta_path: Path

    def load_credentials(self) -> Credentials | None: ...

    def has_session(self) -> bool: ...

    def clear_session(self) -> bool: ...

    def write_session_metadata(self, payload: dict[str, str]) -> None: ...


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
