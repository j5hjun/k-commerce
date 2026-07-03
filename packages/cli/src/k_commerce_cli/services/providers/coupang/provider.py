from __future__ import annotations

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import BaseProvider, Browser, Store
from k_commerce_cli.services.types import ProviderName

from .auth import CoupangAuthService
from .cart.service import CoupangCartService
from .orders import CoupangOrderService
from .review.service import CoupangReviewService
from .search.service import CoupangSearchService


class CoupangProvider(
    BaseProvider[
        CoupangAuthService,
        CoupangOrderService,
        CoupangReviewService,
        CoupangSearchService,
        CoupangCartService,
    ]
):
    auth_service_cls = CoupangAuthService
    order_service_cls = CoupangOrderService
    review_service_cls = CoupangReviewService
    search_service_cls = CoupangSearchService
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


__all__ = ["CoupangProvider"]
