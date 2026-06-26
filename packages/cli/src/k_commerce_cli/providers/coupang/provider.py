from __future__ import annotations

from k_commerce_cli.providers.base import Provider
from k_commerce_cli.providers.constants import ProviderName

from .auth import CoupangAuthProvider
from .order import CoupangOrderProvider


class CoupangProvider(Provider):
    name = ProviderName.COUPANG

    def __init__(self) -> None:
        self.auth = CoupangAuthProvider()
        self.order = CoupangOrderProvider(self.auth)
