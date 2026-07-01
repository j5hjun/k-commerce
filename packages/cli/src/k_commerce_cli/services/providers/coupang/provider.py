from __future__ import annotations

from k_commerce_cli.services.base import BaseProvider

from .auth import CoupangAuthService
from .orders import CoupangOrderService
from .review.service import CoupangReviewService
from .search.service import CoupangSearchService


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
    search_service_cls = CoupangSearchService


__all__ = ["CoupangProvider"]
