from pathlib import Path
from unittest.mock import ANY
from unittest.mock import AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.services.types import (
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
    update_provider = Mock()
    cart_session = Mock()
    cart_session.list_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(selected_item,),
        )
    )
    cart_session.refresh_cart = AsyncMock(
        return_value=ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):\n\n수정됨",
            items=(
                CartItem(
                    index=1,
                    product_name=selected_item.product_name,
                    option_text=selected_item.option_text,
                    quantity=3,
                    unit_price="5,900원",
                    total_price="17,700원",
                    product_id=selected_item.product_id,
                    vendor_item_id=selected_item.vendor_item_id,
                    item_id=selected_item.item_id,
                ),
            ),
        )
    )
    cart_session.update_cart_quantity = AsyncMock(
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
    update_provider.cart_session = Mock(return_value=_AsyncContext(cart_session))

    with (
        patch(
            "k_commerce_cli.commands.cart.get_provider",
            return_value=update_provider,
        ) as get_provider,
        patch(
            "k_commerce_cli.commands.cart.prompt_cart_item",
            AsyncMock(side_effect=[selected_item, None]),
        ),
        patch("k_commerce_cli.commands.cart.prompt_quantity", AsyncMock(return_value=3)),
        patch("k_commerce_cli.commands.cart.asyncio.sleep", AsyncMock()),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    assert get_provider.call_count == 1
    update_provider.cart_session.assert_called_once_with()
    cart_session.list_cart.assert_awaited_once_with()
    cart_session.refresh_cart.assert_awaited_once_with()
    cart_session.update_cart_quantity.assert_awaited_once()
    request = cart_session.update_cart_quantity.await_args.args[0]
    assert request.vendor_item_id == "95103608027"
    assert request.item_id == "44245695211"
    assert request.quantity == 3
    assert "[ok] 루미즈 초경량 자외선차단 접이식 3단 양산 우산 / 베이지 / 3개 / 17,700원" in result.output
    assert "장바구니 상품 (1건):\n\n수정됨" not in result.output


@pytest.mark.anyio
async def test_cart_quantity_command_exits_cleanly_on_exit_choice_string() -> None:
    provider = Mock()
    cart_session = Mock()
    cart_session.list_cart = AsyncMock(
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
    provider.cart_session = Mock(return_value=_AsyncContext(cart_session))

    with (
        patch("k_commerce_cli.commands.cart.get_provider", return_value=provider),
        patch("k_commerce_cli.commands.cart.prompt_cart_item", AsyncMock(return_value="나가기")),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang", "--quantity"])

    assert result.exit_code == 0
    cart_session.list_cart.assert_awaited_once_with()


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
