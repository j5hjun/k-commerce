from __future__ import annotations

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import BaseProvider, Browser, Store

from .auth import CoupangAuthService
from .orders import CoupangOrderService
from .review.service import CoupangReviewService


class CoupangProvider(
    BaseProvider[CoupangAuthService, CoupangOrderService, CoupangReviewService]
):
    auth_service_cls = CoupangAuthService
    order_service_cls = CoupangOrderService
    review_service_cls = CoupangReviewService

    def __init__(
        self,
        provider: str,
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
