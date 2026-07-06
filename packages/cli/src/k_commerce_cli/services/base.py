from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncContextManager, Generic, Protocol, TypeVar

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartQuantityUpdateRequest,
    CartQuantityUpdateResult,
    ListCartResult,
    ListEditableReviewsResult,
    ListReviewsResult,
    ListReviewableResult,
    LoginResult,
    LogoutResult,
    DeliveryTrackingResult,
    OrderResult,
    ProviderName,
    ReviewDeleteRequest,
    ReviewDeleteResult,
    ReviewEditRequest,
    ReviewEditResult,
    ReviewUploadRequest,
    ReviewUploadResult,
    StatusResult,
)

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
    orders_path: Path
    cart_path: Path

    def load_credentials(self) -> Credentials | None: ...

    def has_session(self) -> bool: ...

    def clear_session(self) -> bool: ...

    def write_session_metadata(self, payload: dict[str, str]) -> None: ...

    def load_orders(self) -> dict[str, Any] | None: ...

    def write_orders(self, payload: dict[str, Any]) -> None: ...

    def load_cart(self) -> dict[str, Any] | None: ...

    def write_cart(self, payload: dict[str, Any]) -> None: ...


class Provider(Protocol):
    async def login(self) -> LoginResult: ...

    async def status(self) -> StatusResult: ...

    async def logout(self) -> LogoutResult: ...

    async def list_cart(self, refresh: bool = False) -> ListCartResult: ...

    async def update_cart_quantity(
        self, request: CartQuantityUpdateRequest
    ) -> CartQuantityUpdateResult: ...

    async def delete_cart_item(self, request: CartDeleteRequest) -> CartDeleteResult: ...

    async def delete_cart_items(
        self, requests: tuple[CartDeleteRequest, ...]
    ) -> CartDeleteResult: ...

    async def clear_cart(self) -> CartDeleteResult: ...

    def cart_session(self) -> AsyncContextManager["CartSession"]: ...

    async def list_reviewable(self) -> ListReviewableResult: ...

    async def list_editable(self) -> ListEditableReviewsResult: ...

    async def list_reviews(self) -> ListReviewsResult: ...

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult: ...

    async def edit_review(self, request: ReviewEditRequest) -> ReviewEditResult: ...

    async def delete_review(self, request: ReviewDeleteRequest) -> ReviewDeleteResult: ...

    async def list_orders(
        self,
        refresh: bool = False,
        failed_only: bool = False,
    ) -> OrderResult: ...

    async def get_delivery_tracking(
        self,
        order_id: int,
        shipment_box_id: str,
    ) -> DeliveryTrackingResult: ...

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> SearchProductResult: ...


class AuthService(Protocol):
    async def login(self) -> LoginResult: ...

    async def status(self) -> StatusResult: ...

    async def logout(self) -> LogoutResult: ...


class OrderService(Protocol):
    async def list_orders(
        self,
        refresh: bool = False,
        failed_only: bool = False,
    ) -> OrderResult: ...

    async def get_delivery_tracking(
        self,
        order_id: int,
        shipment_box_id: str,
    ) -> DeliveryTrackingResult: ...


class ReviewService(Protocol):
    async def list_reviewable(self) -> ListReviewableResult: ...

    async def list_editable(self) -> ListEditableReviewsResult: ...

    async def list_reviews(self) -> ListReviewsResult: ...

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult: ...

    async def edit_review(self, request: ReviewEditRequest) -> ReviewEditResult: ...

    async def delete_review(self, request: ReviewDeleteRequest) -> ReviewDeleteResult: ...


class SearchService(Protocol):
    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> SearchProductResult: ...


class CartService(Protocol):
    async def list_cart(self, refresh: bool = False) -> ListCartResult: ...

    async def update_cart_quantity(
        self, request: CartQuantityUpdateRequest
    ) -> CartQuantityUpdateResult: ...

    async def delete_cart_item(self, request: CartDeleteRequest) -> CartDeleteResult: ...

    async def delete_cart_items(
        self, requests: tuple[CartDeleteRequest, ...]
    ) -> CartDeleteResult: ...

    async def clear_cart(self) -> CartDeleteResult: ...

    def cart_session(self) -> AsyncContextManager["CartSession"]: ...


class CartSession(Protocol):
    async def list_cart(self) -> ListCartResult: ...

    async def refresh_cart(self) -> ListCartResult: ...

    async def update_cart_quantity(
        self, request: CartQuantityUpdateRequest
    ) -> CartQuantityUpdateResult: ...

    async def delete_cart_item(self, request: CartDeleteRequest) -> CartDeleteResult: ...

    async def delete_cart_items(
        self, requests: tuple[CartDeleteRequest, ...]
    ) -> CartDeleteResult: ...

    async def clear_cart(self) -> CartDeleteResult: ...


AuthServiceT = TypeVar("AuthServiceT", bound=AuthService)
OrderServiceT = TypeVar("OrderServiceT", bound=OrderService)
ReviewServiceT = TypeVar("ReviewServiceT", bound=ReviewService)
SearchServiceT = TypeVar("SearchServiceT", bound=SearchService)
CartServiceT = TypeVar("CartServiceT", bound=CartService)


class BaseProvider(
    Provider,
    Generic[
        AuthServiceT,
        OrderServiceT,
        ReviewServiceT,
        SearchServiceT,
        CartServiceT,
    ],
):
    auth_service_cls: type[AuthServiceT]
    order_service_cls: type[OrderServiceT]
    review_service_cls: type[ReviewServiceT]
    search_service_cls: type[SearchServiceT]
    cart_service_cls: type[CartServiceT]

    def __init__(
        self,
        provider: ProviderName,
        terminal: Terminal | None = None,
        browser: Browser | None = None,
        store: Store | None = None,
    ) -> None:
        self.provider = provider
        self.terminal = terminal
        self.browser = browser
        self.store = store

    @cached_property
    def auth_service(self) -> AuthServiceT:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.auth_service_cls(
            provider=self.provider,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    @cached_property
    def order_service(self) -> OrderServiceT:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.order_service_cls(
            provider=self.provider,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    @cached_property
    def review_service(self) -> ReviewServiceT:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.review_service_cls(
            provider=self.provider,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    @cached_property
    def search_service(self) -> SearchServiceT:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.search_service_cls(
            provider_name=self.provider.value,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    @cached_property
    def cart_service(self) -> CartServiceT:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.cart_service_cls(
            provider=self.provider,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    async def login(self) -> LoginResult:
        return await self.auth_service.login()

    async def status(self) -> StatusResult:
        return await self.auth_service.status()

    async def logout(self) -> LogoutResult:
        return await self.auth_service.logout()

    async def list_cart(self, refresh: bool = False) -> ListCartResult:
        return await self.cart_service.list_cart(refresh=refresh)

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        return await self.cart_service.update_cart_quantity(request)

    async def delete_cart_item(self, request: CartDeleteRequest) -> CartDeleteResult:
        return await self.cart_service.delete_cart_item(request)

    async def delete_cart_items(
        self,
        requests: tuple[CartDeleteRequest, ...],
    ) -> CartDeleteResult:
        return await self.cart_service.delete_cart_items(requests)

    async def clear_cart(self) -> CartDeleteResult:
        return await self.cart_service.clear_cart()

    def cart_session(self) -> AsyncContextManager[CartSession]:
        return self.cart_service.cart_session()

    async def list_reviewable(self) -> ListReviewableResult:
        return await self.review_service.list_reviewable()

    async def list_editable(self) -> ListEditableReviewsResult:
        return await self.review_service.list_editable()

    async def list_reviews(self) -> ListReviewsResult:
        return await self.review_service.list_reviews()

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        return await self.review_service.upload_review(request)

    async def edit_review(self, request: ReviewEditRequest) -> ReviewEditResult:
        return await self.review_service.edit_review(request)

    async def delete_review(self, request: ReviewDeleteRequest) -> ReviewDeleteResult:
        return await self.review_service.delete_review(request)

    async def list_orders(
        self,
        refresh: bool = False,
        failed_only: bool = False,
    ) -> OrderResult:
        return await self.order_service.list_orders(
            refresh=refresh,
            failed_only=failed_only,
        )

    async def get_delivery_tracking(
        self,
        order_id: int,
        shipment_box_id: str,
    ) -> DeliveryTrackingResult:
        return await self.order_service.get_delivery_tracking(
            order_id=order_id,
            shipment_box_id=shipment_box_id,
        )

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> SearchProductResult:
        return await self.search_service.search_products(
            keyword,
            category=category,
            sort=sort,
            max_results=max_results,
        )
