from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, TYPE_CHECKING

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.types import LoginResult, LogoutResult, StatusResult, ListReviewableResult, ReviewUploadRequest, ReviewUploadResult

if TYPE_CHECKING:
    from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult

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

    async def evaluate(self, expression: str) -> Any: ...


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
    async def login(self) -> LoginResult: ...

    async def status(self) -> StatusResult: ...

    async def logout(self) -> LogoutResult: ...

    async def list_reviewable(self) -> ListReviewableResult: ...

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult: ...

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> "SearchProductResult": ...
