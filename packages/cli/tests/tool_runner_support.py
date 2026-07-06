from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.types import CartQuantityUpdateRequest, CartQuantityUpdateResult, ProviderName
from k_commerce_cli.services.types.auth import LoginResult, LogoutResult, StatusResult


@dataclass(frozen=True, slots=True)
class ProviderCall:
    name: str
    request: CartQuantityUpdateRequest | None = None


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[ProviderCall] = []

    async def login(self) -> LoginResult:
        self.calls.append(ProviderCall("login"))
        return LoginResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그인 성공",
        )

    async def status(self) -> StatusResult:
        self.calls.append(ProviderCall("status"))
        return StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )

    async def logout(self) -> LogoutResult:
        self.calls.append(ProviderCall("logout"))
        return LogoutResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그아웃 완료",
        )

    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        return CartQuantityUpdateResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 수량 수정 성공",
            quantity=request.quantity,
            product_id=request.product_id,
            vendor_item_id=request.vendor_item_id,
            item_id=request.item_id,
        )


@contextmanager
def patched_tool_provider(fake_provider: FakeProvider) -> Generator[None]:
    def get_provider(
        provider: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> FakeProvider:
        assert provider == "coupang"
        assert root_dir is None
        assert terminal is None
        return fake_provider

    with patch("k_commerce_cli.commands.tool_runner.default_get_provider", side_effect=get_provider):
        yield


def write_cart_update_request(tmp_path: Path) -> Path:
    request_file = tmp_path / "cart-update.json"
    _ = request_file.write_text(
        json.dumps(
            {
                "provider": "coupang",
                "product_id": "p",
                "vendor_item_id": "v",
                "item_id": "i",
                "quantity": 3,
            }
        ),
        encoding="utf-8",
    )
    return request_file
