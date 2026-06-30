from k_commerce_cli.services.providers.coupang.cart.service import CoupangCartService
from k_commerce_cli.services.providers.coupang.cart.state import CoupangCartState
from k_commerce_cli.services.providers.coupang.cart.type import (
    _CartItemData,
    _ListCartBrowserResult,
)
from k_commerce_cli.services.types import CartQuantityUpdateRequest, ProviderName


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
