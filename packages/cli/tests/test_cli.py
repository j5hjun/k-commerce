from pathlib import Path
from unittest.mock import ANY
from unittest.mock import AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.services.types import ListCartResult
from k_commerce_cli.services.types.auth import LoginResult, LogoutResult, StatusResult
from k_commerce_cli.services.types import ProviderName
from k_commerce_cli.services.providers.coupang.types import (
    CoupangOrderList,
    CoupangOrderListResult,
    CoupangOrderMeta,
    CoupangOrderSummary,
)

RUNNER = CliRunner()


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
