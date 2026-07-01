from pathlib import Path
from unittest.mock import ANY
from unittest.mock import AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.services.types import (
    CartDeleteResult,
    CartItem,
    CartQuantityUpdateResult,
    ListCartResult,
)
from k_commerce_cli.services.types.auth import LoginResult, LogoutResult, StatusResult
from k_commerce_cli.services.types import ProviderName
from k_commerce_cli.services.providers.coupang.types import (
    CoupangOrderList,
    CoupangOrderListResult,
    CoupangOrderMeta,
    CoupangOrderSummary,
)

RUNNER = CliRunner()


class _AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.anyio
async def test_app_help_lists_status_command() -> None:
    result = await RUNNER.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "status" in result.output
    assert "login status" not in result.output


@pytest.mark.anyio
async def test_login_help_does_not_list_status_subcommand() -> None:
    result = await RUNNER.invoke(app, ["login", "--help"])

    assert result.exit_code == 0
    assert "status" not in result.output


@pytest.mark.anyio
async def test_order_help_lists_list_subcommand() -> None:
    result = await RUNNER.invoke(app, ["order", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output


@pytest.mark.anyio
async def test_login_coupang_command_prints_login_message_once() -> None:
    provider = Mock()
    provider.login = AsyncMock(
        return_value=LoginResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그인 성공",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.login.assert_awaited_once_with()


@pytest.mark.anyio
async def test_login_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.login = AsyncMock(
        return_value=LoginResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그인 성공",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang", "--root_dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.login.assert_awaited_once_with()


@pytest.mark.anyio
async def test_status_coupang_command_prints_status_message_once() -> None:
    provider = Mock()
    provider.status = AsyncMock(
        return_value=StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )

    with patch("k_commerce_cli.commands.status.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["status", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.status.assert_awaited_once_with()


@pytest.mark.anyio
async def test_status_coupang_command_passes_root_dir_to_service(
    tmp_path: Path,
) -> None:
    provider = Mock()
    provider.status = AsyncMock(
        return_value=StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )

    with patch("k_commerce_cli.commands.status.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["status", "coupang", "--root_dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.status.assert_awaited_once_with()


@pytest.mark.anyio
async def test_cart_coupang_command_lists_cart() -> None:
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(),
        )
    )

    with patch("k_commerce_cli.commands.cart.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["cart", "coupang"])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.list_cart.assert_awaited_once_with()


@pytest.mark.anyio
async def test_cart_coupang_command_handles_browser_closed_gracefully() -> None:
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=False,
            message="브라우저가 닫혀 장바구니 작업을 취소했습니다.",
            items=(),
        )
    )

    with patch("k_commerce_cli.commands.cart.get_provider", return_value=provider):
        result = await RUNNER.invoke(app, ["cart", "coupang"])

    assert result.exit_code == 0
    assert "[error] 브라우저가 닫혀 장바구니 작업을 취소했습니다." in result.output
    assert "Traceback" not in result.output


@pytest.mark.anyio
async def test_cart_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(),
        )
    )

    with patch("k_commerce_cli.commands.cart.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["cart", "coupang", "--root_dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.list_cart.assert_awaited_once_with()
    assert "장바구니에 담긴 상품이 없습니다." in result.output


@pytest.mark.anyio
async def test_cart_quantity_command_updates_selected_item_quantity() -> None:
    selected_item = CartItem(
        index=1,
        product_name="루미즈 초경량 자외선차단 접이식 3단 양산 우산",
        option_text="베이지",
        quantity=1,
        unit_price="5,900원",
        total_price="5,900원",
        product_id="9459571406",
        vendor_item_id="95103608027",
        item_id="44245695211",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(selected_item,),
        )
    )
    provider.update_cart_quantity = AsyncMock(
        return_value=CartQuantityUpdateResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 수량 수정 성공",
            quantity=3,
            product_id=selected_item.product_id,
            vendor_item_id=selected_item.vendor_item_id,
            item_id=selected_item.item_id,
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ) as get_provider,
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, None]),
        ),
        patch("k_commerce_cli.commands.cart.prompt_quantity", AsyncMock(return_value=3)),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_continue",
            AsyncMock(return_value=False),
        ) as prompt_cart_continue,
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    assert get_provider.call_count == 2
    get_provider.assert_any_call("coupang", root_dir=None, terminal=None)
    get_provider.assert_any_call("coupang", root_dir=None, terminal=ANY)
    provider.list_cart.assert_awaited_once()
    provider.update_cart_quantity.assert_awaited_once()
    request = provider.update_cart_quantity.await_args.args[0]
    assert request.vendor_item_id == "95103608027"
    assert request.item_id == "44245695211"
    assert request.quantity == 3
    prompt_cart_continue.assert_awaited_once()
    assert "[ok] 쿠팡 장바구니 수량 수정 성공" in result.output
    assert "루미즈 초경량 자외선차단 접이식 3단 양산 우산 / 베이지 / 3개" in result.output


@pytest.mark.anyio
async def test_cart_quantity_command_shows_applied_quantity_when_capped() -> None:
    selected_item = CartItem(
        index=1,
        product_name="도치코 헤어커치프 헤드스카프 두건 헤어밴드 레이스",
        option_text="클리어 화이트2개입",
        quantity=1,
        unit_price="5,690원",
        total_price="5,690원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(selected_item,),
        )
    )
    provider.update_cart_quantity = AsyncMock(
        return_value=CartQuantityUpdateResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 수량 수정 성공",
            quantity=10,
            product_id="1",
            vendor_item_id="2",
            item_id="3",
            notice="최대 구매 가능한 수량으로 변경되었습니다.",
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, None]),
        ),
        patch("k_commerce_cli.commands.cart.prompt_quantity", AsyncMock(return_value=100_000_000)),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_continue",
            AsyncMock(return_value=False),
        ),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    assert "[warn] 최대 구매 가능한 수량으로 변경되었습니다." in result.output
    assert "도치코 헤어커치프 헤드스카프 두건 헤어밴드 레이스 / 클리어 화이트2개입 / 10개" in result.output
    assert "100000000개" not in result.output


@pytest.mark.anyio
async def test_cart_quantity_command_reloads_list_when_user_continues() -> None:
    selected_item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        side_effect=[
            ListCartResult(
                provider="coupang",
                success=True,
                message="장바구니 상품 (1건):",
                items=(selected_item,),
            ),
            ListCartResult(
                provider="coupang",
                success=True,
                message="장바구니 상품 (1건):",
                items=(selected_item,),
            ),
        ]
    )
    provider.update_cart_quantity = AsyncMock(
        return_value=CartQuantityUpdateResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 수량 수정 성공",
            quantity=2,
            product_id="1",
            vendor_item_id="2",
            item_id="3",
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, None]),
        ),
        patch("k_commerce_cli.commands.cart.prompt_quantity", AsyncMock(return_value=2)),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_continue",
            AsyncMock(return_value=True),
        ),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    assert provider.list_cart.await_count == 2
    assert provider.update_cart_quantity.await_count == 1


@pytest.mark.anyio
async def test_cart_quantity_command_exits_cleanly_on_exit_choice_string() -> None:
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(
                CartItem(
                    index=1,
                    product_name="테스트 상품",
                    option_text="옵션",
                    quantity=1,
                    unit_price="1,000원",
                    total_price="1,000원",
                    product_id="1",
                    vendor_item_id="2",
                    item_id="3",
                ),
            ),
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch("k_commerce_cli.commands.cart.prompt_cart_item", AsyncMock(return_value="나가기")),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    provider.list_cart.assert_awaited_once()
    assert "장바구니 수량 수정을 종료했습니다." in result.output


@pytest.mark.anyio
async def test_cart_quantity_command_shows_error_when_update_fails() -> None:
    selected_item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(selected_item,),
        )
    )
    provider.update_cart_quantity = AsyncMock(
        return_value=CartQuantityUpdateResult(
            provider="coupang",
            success=False,
            message="브라우저가 닫혀 장바구니 작업을 취소했습니다.",
            quantity=3,
            product_id="1",
            vendor_item_id="2",
            item_id="3",
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, None]),
        ),
        patch("k_commerce_cli.commands.cart.prompt_quantity", AsyncMock(return_value=3)),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    assert "[error] 브라우저가 닫혀 장바구니 작업을 취소했습니다." in result.output
    assert "Error:" not in result.output
    provider.update_cart_quantity.assert_awaited_once()


@pytest.mark.anyio
async def test_cart_delete_command_rejects_conflicting_flags() -> None:
    result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity", "--delete"])
    assert result.exit_code == 2
    assert "--list, --quantity, --delete는 함께 사용할 수 없습니다." in result.output


@pytest.mark.anyio
async def test_cart_delete_single_item_flow() -> None:
    selected_item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=2,
        unit_price="1,000원",
        total_price="2,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(selected_item,),
        )
    )
    provider.delete_cart_item = AsyncMock(
        return_value=CartDeleteResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 상품 삭제 성공",
            deleted_count=1,
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_delete_mode",
            AsyncMock(return_value="single"),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, "exit"]),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_bulk_delete_confirmation",
            AsyncMock(return_value="confirm"),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_continue",
            AsyncMock(return_value=False),
        ),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--delete"])

    assert result.exit_code == 0
    provider.delete_cart_item.assert_awaited_once()
    assert "[ok] 쿠팡 장바구니 상품 삭제 성공" in result.output
    assert "삭제할 상품 (1건):" in result.output
    assert "테스트 상품 / 옵션 / 2개" in result.output


@pytest.mark.anyio
async def test_cart_delete_all_flow() -> None:
    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(item,),
        )
    )
    provider.clear_cart = AsyncMock(
        return_value=CartDeleteResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 비우기 성공",
            deleted_count=0,
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_delete_mode",
            AsyncMock(return_value="all"),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_clear_cart_action",
            AsyncMock(return_value="clear"),
        ),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--delete"])

    assert result.exit_code == 0
    provider.clear_cart.assert_awaited_once()
    assert "[ok] 쿠팡 장바구니 비우기 성공" in result.output
    provider.list_cart.assert_not_awaited()


@pytest.mark.anyio
async def test_cart_delete_selected_items_flow() -> None:
    items = (
        CartItem(
            index=1,
            product_name="테스트 상품 A",
            option_text="옵션 A",
            quantity=1,
            unit_price="1,000원",
            total_price="1,000원",
            product_id="1",
            vendor_item_id="11",
            item_id="101",
        ),
        CartItem(
            index=2,
            product_name="테스트 상품 B",
            option_text="옵션 B",
            quantity=2,
            unit_price="2,000원",
            total_price="4,000원",
            product_id="2",
            vendor_item_id="22",
            item_id="202",
        ),
    )
    selected = items[:2]
    provider = Mock()
    provider.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (2건):",
            items=items,
        )
    )
    provider.delete_cart_items = AsyncMock(
        return_value=CartDeleteResult(
            provider="coupang",
            success=True,
            message="쿠팡 장바구니 상품 2개 삭제 성공",
            deleted_count=2,
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            side_effect=[provider, provider],
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_delete_mode",
            AsyncMock(return_value="selected"),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_items",
            AsyncMock(return_value=selected),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_bulk_delete_confirmation",
            AsyncMock(return_value="confirm"),
        ),
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_continue",
            AsyncMock(return_value=False),
        ),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--delete"])

    assert result.exit_code == 0
    provider.delete_cart_items.assert_awaited_once()
    assert "[ok] 쿠팡 장바구니 상품 2개 삭제 성공" in result.output
    assert "테스트 상품 A / 옵션 A / 1개" in result.output
    assert "테스트 상품 B / 옵션 B / 2개" in result.output
    assert "삭제할 상품 (2건):" in result.output


@pytest.mark.anyio
async def test_status_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.commands.status.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ) as get_provider:
        result = await RUNNER.invoke(app, ["status", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value for provider: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid", root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_status_missing_provider_shows_parse_error() -> None:
    with patch("k_commerce_cli.commands.status.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["status"])

    assert result.exit_code == 2
    assert "Missing argument 'PROVIDER'" in result.output
    get_provider.assert_not_called()


@pytest.mark.anyio
async def test_login_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.commands.login.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang", "extra"])

    assert result.exit_code == 2
    assert "Got unexpected extra argument (extra)" in result.output
    get_provider.assert_not_called()


@pytest.mark.anyio
async def test_status_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.commands.status.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["status", "coupang", "extra"])

    assert result.exit_code == 2
    assert "Got unexpected extra argument (extra)" in result.output
    get_provider.assert_not_called()


@pytest.mark.anyio
async def test_login_invalid_provider_command_is_rejected_by_parser() -> None:
    with patch(
        "k_commerce_cli.commands.login.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ) as get_provider:
        result = await RUNNER.invoke(app, ["login", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value for provider: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid", root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_logout_coupang_command_prints_logout_message_once() -> None:
    provider = Mock()
    provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.logout.assert_awaited_once_with()


@pytest.mark.anyio
async def test_logout_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.logout.assert_awaited_once_with()


@pytest.mark.anyio
async def test_order_list_command_prints_summary_once() -> None:
    provider = Mock()
    provider.list_orders = AsyncMock(
        return_value=CoupangOrderListResult(
            message="주문 수집 완료: 총 1건, 추가 0건, 변경 1건, 삭제 0건",
            payload=CoupangOrderList(
                meta=CoupangOrderMeta(
                    provider=ProviderName.COUPANG,
                    collectedAt="2026-06-28T12:00:00+09:00",
                    years=["2026"],
                    failedPages=[],
                    refresh=False,
                    summary=CoupangOrderSummary(
                        totalOrders=1,
                        addedOrders=0,
                        updatedOrders=1,
                        deletedOrders=0,
                    ),
                ),
                orders=[],
            ),
        )
    )

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=None, terminal=ANY)
    provider.list_orders.assert_awaited_once_with(refresh=False, failed_only=False)


@pytest.mark.anyio
async def test_order_list_refresh_passes_refresh_flag(tmp_path: Path) -> None:
    provider = Mock()
    provider.list_orders = AsyncMock(
        return_value=CoupangOrderListResult(
            message="주문 새로 생성 완료: 총 1건",
            payload=CoupangOrderList(
                meta=CoupangOrderMeta(
                    provider=ProviderName.COUPANG,
                    collectedAt="2026-06-28T12:00:00+09:00",
                    years=["2026"],
                    failedPages=[],
                    refresh=True,
                    summary=CoupangOrderSummary(
                        totalOrders=1,
                        addedOrders=0,
                        updatedOrders=0,
                        deletedOrders=0,
                    ),
                ),
                orders=[],
            ),
        )
    )

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(
            app,
            ["order", "list", "coupang", "--refresh", "--root-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.list_orders.assert_awaited_once_with(refresh=True, failed_only=False)


@pytest.mark.anyio
async def test_order_list_failed_only_passes_failed_only_flag(tmp_path: Path) -> None:
    provider = Mock()
    provider.list_orders = AsyncMock(
        return_value=CoupangOrderListResult(
            message="주문 수집 완료: 총 1건, 추가 1건, 변경 0건, 삭제 0건",
            payload=CoupangOrderList(
                meta=CoupangOrderMeta(
                    provider=ProviderName.COUPANG,
                    collectedAt="2026-06-28T12:00:00+09:00",
                    years=["2026"],
                    failedPages=[],
                    refresh=False,
                    summary=CoupangOrderSummary(
                        totalOrders=1,
                        addedOrders=1,
                        updatedOrders=0,
                        deletedOrders=0,
                    ),
                ),
                orders=[],
            ),
        )
    )

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(
            app,
            ["order", "list", "coupang", "--failed-only", "--root-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    get_provider.assert_called_once_with("coupang", root_dir=tmp_path, terminal=ANY)
    provider.list_orders.assert_awaited_once_with(refresh=False, failed_only=True)


@pytest.mark.anyio
async def test_order_list_rejects_refresh_with_failed_only() -> None:
    result = await RUNNER.invoke(
        app,
        ["order", "list", "coupang", "--refresh", "--failed-only"],
    )

    assert result.exit_code != 0
    assert "--refresh and --failed-only cannot be used together." in result.output
