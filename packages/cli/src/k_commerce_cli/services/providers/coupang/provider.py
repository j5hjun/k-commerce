from __future__ import annotations

from functools import cached_property

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import BaseProvider, Browser, Store
from k_commerce_cli.services.types import ListCartResult, ProviderName

from .auth import CoupangAuthService
from .cart.service import CoupangCartService
from .orders import CoupangOrderService
from .review.service import CoupangReviewService
from .search.service import CoupangSearchService
from .search.type import SearchProductResult


class CoupangProvider(
    BaseProvider[
        CoupangAuthService,
        CoupangOrderService,
        CoupangReviewService,
        CoupangSearchService,
    ]
):
    auth_service_cls = CoupangAuthService
    order_service_cls = CoupangOrderService
    review_service_cls = CoupangReviewService
    cart_service_cls = CoupangCartService

    def __init__(
        self,
        provider: ProviderName,
        terminal: Terminal | None = None,
        browser: Browser | None = None,
        store: Store | None = None,
    ) -> None:
        super().__init__(
            provider=provider,
            terminal=terminal,
            browser=browser,
            store=store,
        )

    @cached_property
    def search_service(self) -> CoupangSearchService:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return CoupangSearchService(
            provider_name=self.provider.value,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
        )

    @cached_property
    def cart_service(self) -> CoupangCartService:
        if self.store is None or self.browser is None:
            raise ValueError("Provider requires both store and browser before use")
        return self.cart_service_cls(
            provider=self.provider,
            store=self.store,
            browser=self.browser,
            terminal=self.terminal,
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

    async def list_cart(self) -> ListCartResult:
        return await self.cart_service.list_cart()


__all__ = ["CoupangProvider"]
