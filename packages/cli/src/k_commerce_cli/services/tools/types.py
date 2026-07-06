from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Provider
from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.types import (
    CartDeleteResult,
    CartQuantityUpdateResult,
    ListCartResult,
    ListEditableReviewsResult,
    ListReviewableResult,
    LoginResult,
    LogoutResult,
    OrderResult,
    ReviewDeleteResult,
    ReviewEditResult,
    ReviewUploadResult,
    StatusResult,
)

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
ToolInvocationResult: TypeAlias = (
    list[str]
    | JSONValue
    | LoginResult
    | StatusResult
    | LogoutResult
    | OrderResult
    | ListCartResult
    | CartQuantityUpdateResult
    | CartDeleteResult
    | SearchProductResult
    | ListReviewableResult
    | ListEditableReviewsResult
    | ReviewUploadResult
    | ReviewEditResult
    | ReviewDeleteResult
)


class ToolProviderFactory(Protocol):
    def __call__(
        self,
        provider: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> Provider: ...


class ToolProviderLister(Protocol):
    def __call__(self) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class ToolRuntimeOptions:
    root_dir: Path | None = None
    terminal: Terminal | None = None
    get_provider: ToolProviderFactory | None = None
    list_providers: ToolProviderLister | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ToolRequestError(Exception):
    tool_name: str
    message: str
    field: str | None = None

    def __str__(self) -> str:
        if self.field is None:
            return f"{self.tool_name}: {self.message}"
        return f"{self.tool_name}.{self.field}: {self.message}"
