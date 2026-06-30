from __future__ import annotations

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import BaseProvider, Browser, Store
from k_commerce_cli.services.types import ProviderName

from .auth import CoupangAuthService
from .orders import CoupangOrderService
from .review.service import CoupangReviewService
from .search.service import CoupangSearchService


class CoupangProvider(
    BaseProvider[CoupangAuthService, CoupangOrderService, CoupangReviewService]
):
    auth_service_cls = CoupangAuthService
    order_service_cls = CoupangOrderService
    review_service_cls = CoupangReviewService

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
        )
        self._review = CoupangReviewService(
            provider_name=provider_name,
            store=self.store,
            browser=self._browser,
            terminal=terminal,
        )
        self._search = CoupangSearchService(
            provider_name=provider_name,
            store=self.store,
            browser=self._browser,
            terminal=terminal,
        )
        self._search = CoupangSearchService(
            provider_name=provider_name,
            store=self.store,
            browser=self._browser,
            terminal=terminal,
        )

    async def login(self) -> LoginResult:
        return await self._auth.login()

    async def status(self) -> StatusResult:
        return await self._auth.status()

    async def logout(self) -> LogoutResult:
        return await self._auth.logout()

    async def list_reviewable(self) -> ListReviewableResult:
        return await self._review.list_reviewable()

    async def upload_review(self, request: ReviewUploadRequest) -> ReviewUploadResult:
        return await self._review.upload_review(request)

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
    ) -> SearchProductResult:
        return await self._search.search_products(
            keyword,
            category=category,
            sort=sort,
            max_results=max_results,
        )


__all__ = ["CoupangProvider"]
