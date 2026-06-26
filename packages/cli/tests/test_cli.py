from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.types import (
    LoginResult,
    LogoutResult,
    OrderListEntry,
    OrderListResult,
    StatusResult,
)

RUNNER = CliRunner()


@pytest.mark.anyio
async def test_order_list_coupang_command_renders_readable_order_lines() -> None:
    order_provider = Mock()
    order_provider.list = AsyncMock(
        return_value=OrderListResult(
            provider="coupang",
            success=True,
            message="주문 2건을 찾았습니다.",
            orders=(
                OrderListEntry(
                    order_date="2026. 6. 26",
                    title="로켓프레시 사과",
                    quantity=2,
                    status="배송완료",
                ),
                OrderListEntry(
                    order_date="2026. 6. 25",
                    title="생수 2L",
                    quantity=1,
                    status="배송중",
                ),
            ),
        )
    )
    provider = Mock(order=order_provider)
    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "상품: 로켓프레시 사과 | 수량: 2 | 상태: 배송완료",
        "상품: 생수 2L | 수량: 1 | 상태: 배송중",
    ]
    get_provider.assert_called_once_with("coupang")
    order_provider.list.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_order_list_coupang_command_normalizes_separator_characters() -> None:
    order_provider = Mock()
    order_provider.list = AsyncMock(
        return_value=OrderListResult(
            provider="coupang",
            success=True,
            message="주문 1건을 찾았습니다.",
            orders=(
                OrderListEntry(
                    order_date="2026. 6. 26",
                    title="로켓\n프레시 | 사과",
                    quantity=2,
                    status="배송|\n완료",
                ),
            ),
        )
    )
    provider = Mock(order=order_provider)

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "상품: 로켓 프레시 사과 | 수량: 2 | 상태: 배송 완료",
    ]
    get_provider.assert_called_once_with("coupang")
    order_provider.list.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_order_coupang_command_uses_list_as_default_subcommand() -> None:
    order_provider = Mock()
    order_provider.list = AsyncMock(
        return_value=OrderListResult(
            provider="coupang",
            success=True,
            message="주문 1건을 찾았습니다.",
            orders=(
                OrderListEntry(
                    order_date="2026. 6. 26",
                    title="로켓프레시 사과",
                    quantity=2,
                    status="배송완료",
                ),
            ),
        )
    )
    provider = Mock(order=order_provider)

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "상품: 로켓프레시 사과 | 수량: 2 | 상태: 배송완료",
    ]
    get_provider.assert_called_once_with("coupang")
    order_provider.list.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_order_list_coupang_command_prints_empty_state_message(
    tmp_path: Path,
) -> None:
    order_provider = Mock()
    order_provider.list = AsyncMock(
        return_value=OrderListResult(
            provider="coupang",
            success=True,
            message="주문 0건을 찾았습니다.",
            orders=(),
        )
    )
    provider = Mock(order=order_provider)

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["조회된 주문이 없습니다."]
    get_provider.assert_called_once_with("coupang")
    order_provider.list.assert_awaited_once_with(root_dir=tmp_path)


@pytest.mark.anyio
async def test_order_list_coupang_command_surfaces_logged_out_failure_message() -> None:
    order_provider = Mock()
    order_provider.list = AsyncMock(
        return_value=OrderListResult(
            provider="coupang",
            success=False,
            message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
            orders=(),
        )
    )
    provider = Mock(order=order_provider)

    with patch("k_commerce_cli.commands.order.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang"])

    assert result.exit_code == 1
    assert result.stdout.splitlines() == ["쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."]
    assert "Error: 쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요." in result.stderr
    get_provider.assert_called_once_with("coupang")
    order_provider.list.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_order_help_lists_list_subcommand() -> None:
    result = await RUNNER.invoke(app, ["order", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output


@pytest.mark.anyio
async def test_order_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.commands.order.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid")


@pytest.mark.anyio
async def test_order_missing_provider_shows_parse_error() -> None:
    with patch("k_commerce_cli.commands.order.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list"])

    assert result.exit_code == 2
    assert "Missing argument 'PROVIDER'" in result.output
    get_provider.assert_not_called()


@pytest.mark.anyio
async def test_order_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.commands.order.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["order", "list", "coupang", "extra"])

    assert result.exit_code == 2
    assert "Got unexpected extra argument (extra)" in result.output
    get_provider.assert_not_called()


@pytest.mark.anyio
async def test_login_help_lists_status_subcommand() -> None:
    result = await RUNNER.invoke(app, ["login", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output


@pytest.mark.anyio
async def test_login_coupang_command_prints_login_message_once() -> None:
    auth_provider = Mock()
    auth_provider.login = AsyncMock(
        return_value=LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 성공"]
    get_provider.assert_called_once_with("coupang")
    auth_provider.login.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_login_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    auth_provider = Mock()
    auth_provider.login = AsyncMock(
        return_value=LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    auth_provider.login.assert_awaited_once_with(root_dir=tmp_path)


@pytest.mark.anyio
async def test_login_status_coupang_command_prints_status_message_once() -> None:
    auth_provider = Mock()
    auth_provider.status = AsyncMock(
        return_value=StatusResult(
            provider="coupang",
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 상태입니다"]
    get_provider.assert_called_once_with("coupang")
    auth_provider.status.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_login_status_coupang_command_passes_root_dir_to_service(
    tmp_path: Path,
) -> None:
    auth_provider = Mock()
    auth_provider.status = AsyncMock(
        return_value=StatusResult(
            provider="coupang",
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    auth_provider.status.assert_awaited_once_with(root_dir=tmp_path)


@pytest.mark.anyio
async def test_login_status_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.commands.login.get_provider",
        side_effect=ValueError("Unsupported provider: invalid"),
    ) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid")


@pytest.mark.anyio
async def test_login_status_missing_provider_shows_parse_error() -> None:
    with patch("k_commerce_cli.commands.login.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status"])

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
async def test_login_status_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.commands.login.get_provider", new=Mock()) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "coupang", "extra"])

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
    assert "Invalid value: Unsupported provider: invalid" in result.output
    get_provider.assert_called_once_with("invalid")


@pytest.mark.anyio
async def test_logout_coupang_command_prints_logout_message_once() -> None:
    auth_provider = Mock()
    auth_provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그아웃 완료"]
    get_provider.assert_called_once_with("coupang")
    auth_provider.logout.assert_awaited_once_with(root_dir=None)


@pytest.mark.anyio
async def test_logout_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    auth_provider = Mock()
    auth_provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )
    provider = Mock(auth=auth_provider)

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    auth_provider.logout.assert_awaited_once_with(root_dir=tmp_path)
