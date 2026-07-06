from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.providers.coupang.cart.service import CoupangCartService
from k_commerce_cli.services.providers.coupang.cart.state import CoupangCartState
from k_commerce_cli.services.providers.coupang.cart.type import (
    _CartItemData,
    _ListCartBrowserResult,
)
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import CartDeleteRequest, CartQuantityUpdateRequest, ProviderName


class _BrowserSpy:
    def __init__(self) -> None:
        self.launch = AsyncMock()
        self.close = AsyncMock()
        self.save_session = AsyncMock()
        self.select = AsyncMock(return_value=None)


def _make_cart_service(root_dir: Path, browser: _BrowserSpy) -> CoupangCartService:
    return CoupangCartService(
        provider=ProviderName.COUPANG,
        store=ProviderStore(ProviderPaths("coupang", root_dir=root_dir)),
        browser=browser,
    )


def test_cart_list_result_formats_cart_items() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    result = service._to_list_result(
        _ListCartBrowserResult(
            state=CoupangCartState.SUCCESS,
            items=(
                _CartItemData(
                    product_name="루미즈 초경량 자외선차단 접이식 3단 양산 우산",
                    option_text="베이지",
                    quantity=1,
                    unit_price="5,900원",
                    total_price="5,900원",
                    product_id="9459571406",
                    vendor_item_id="95103608027",
                    item_id="44245695211",
                ),
                _CartItemData(
                    product_name="Qiaokao 철제 서랍형 수납박스",
                    option_text="1개, 화이트",
                    quantity=2,
                    unit_price="12,990원",
                    total_price="25,980원",
                    product_id="8907011833",
                    vendor_item_id="92996695464",
                    item_id="43815177942",
                ),
            ),
        )
    )

    assert result.success is True
    assert len(result.items) == 2
    assert result.items[0].vendor_item_id == "95103608027"
    assert result.items[0].option_text == "베이지"
    assert result.items[1].quantity == 2
    assert "장바구니 상품 (2건):" in result.message
    assert "Qiaokao 철제 서랍형 수납박스" in result.message
    assert "1개, 화이트" in result.message
    assert "25,980원" in result.message
    assert "92996695464" not in result.message


def test_cart_list_result_handles_empty_cart() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    result = service._to_list_result(
        _ListCartBrowserResult(state=CoupangCartState.SUCCESS, items=())
    )

    assert result.success is True
    assert result.items == ()
    assert result.message == "장바구니에 담긴 상품이 없습니다."


def test_cart_quantity_update_request_requires_positive_quantity() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    result = service._failure_quantity_update_result(
        CartQuantityUpdateRequest(vendor_item_id="95103608027", quantity=0),
        "수량은 1개 이상이어야 합니다.",
    )

    assert result.success is False
    assert result.message == "수량은 1개 이상이어야 합니다."
    assert result.error_code == "validation_error"
    assert result.retryable is False
    assert result.next_tools == ()


def test_cart_quantity_update_result_uses_applied_quantity_and_notice() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    result = service._to_quantity_update_result(
        CartQuantityUpdateRequest(vendor_item_id="95103608027", quantity=100_000_000),
        _ListCartBrowserResult(
            state=CoupangCartState.SUCCESS,
            message="최대 구매 가능한 수량으로 변경되었습니다.",
            applied_quantity=10,
        ),
    )

    assert result.success is True
    assert result.message == "쿠팡 장바구니 수량 수정 성공"
    assert result.notice == "최대 구매 가능한 수량으로 변경되었습니다."
    assert result.quantity == 10


def test_cart_delete_result_success_messages() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    single = service._to_delete_result(
        _ListCartBrowserResult(state=CoupangCartState.SUCCESS),
        deleted_count=1,
    )
    bulk = service._to_delete_result(
        _ListCartBrowserResult(state=CoupangCartState.SUCCESS),
        deleted_count=3,
    )
    clear = service._to_delete_result(
        _ListCartBrowserResult(state=CoupangCartState.SUCCESS),
        deleted_count=0,
    )

    assert single.message == "쿠팡 장바구니 상품 삭제 성공"
    assert bulk.message == "쿠팡 장바구니 상품 3개 삭제 성공"
    assert clear.message == "쿠팡 장바구니 비우기 성공"


@pytest.mark.anyio
async def test_list_cart_returns_not_logged_in_when_session_is_missing(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    service = _make_cart_service(tmp_path, browser)

    result = await service.list_cart()

    assert result.success is False
    assert result.items == ()
    assert result.message == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."
    assert result.error_code == "not_logged_in"
    assert result.retryable is False
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()


@pytest.mark.anyio
async def test_update_cart_quantity_returns_not_logged_in_when_session_is_missing(
    tmp_path: Path,
) -> None:
    browser = _BrowserSpy()
    service = _make_cart_service(tmp_path, browser)

    result = await service.update_cart_quantity(
        CartQuantityUpdateRequest(vendor_item_id="95103608027", quantity=2)
    )

    assert result.success is False
    assert result.error_code == "not_logged_in"
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_cart_item_returns_not_logged_in_when_session_is_missing(
    tmp_path: Path,
) -> None:
    browser = _BrowserSpy()
    service = _make_cart_service(tmp_path, browser)

    result = await service.delete_cart_item(CartDeleteRequest(vendor_item_id="95103608027"))

    assert result.success is False
    assert result.error_code == "not_logged_in"
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_cart_items_returns_not_logged_in_when_session_is_missing(
    tmp_path: Path,
) -> None:
    browser = _BrowserSpy()
    service = _make_cart_service(tmp_path, browser)

    result = await service.delete_cart_items(
        (CartDeleteRequest(vendor_item_id="95103608027"),)
    )

    assert result.success is False
    assert result.error_code == "not_logged_in"
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()


@pytest.mark.anyio
async def test_clear_cart_returns_not_logged_in_when_session_is_missing(tmp_path: Path) -> None:
    browser = _BrowserSpy()
    service = _make_cart_service(tmp_path, browser)

    result = await service.clear_cart()

    assert result.success is False
    assert result.error_code == "not_logged_in"
    assert result.next_tools == ("login",)
    browser.launch.assert_not_awaited()


def test_list_cart_result_handles_browser_closed() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    result = service._to_list_result(
        _ListCartBrowserResult(state=CoupangCartState.BROWSER_CLOSED)
    )

    assert result.success is False
    assert result.message == "브라우저가 닫혀 장바구니 작업을 취소했습니다."
    assert result.error_code == "browser_closed"
    assert result.retryable is True
    assert result.next_tools == ()


@pytest.mark.anyio
async def test_list_cart_with_session_handles_browser_disconnect() -> None:
    service = CoupangCartService(
        provider=ProviderName.COUPANG,
        store=None,  # type: ignore[arg-type]
        browser=None,  # type: ignore[arg-type]
    )

    async def raise_protocol_error(*_args, **_kwargs):
        raise RuntimeError("Session with given id not found.")

    service._list_cart_items = raise_protocol_error  # type: ignore[method-assign]

    result = await service._list_cart_with_session(None)  # type: ignore[arg-type]

    assert result.success is False
    assert result.message == "브라우저가 닫혀 장바구니 작업을 취소했습니다."
