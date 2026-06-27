from pathlib import Path
from unittest.mock import ANY
from unittest.mock import AsyncMock, Mock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult

RUNNER = CliRunner()


@pytest.mark.anyio
async def test_login_help_lists_status_subcommand() -> None:
    result = await RUNNER.invoke(app, ["login", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output


@pytest.mark.anyio
async def test_login_coupang_command_prints_login_message_once() -> None:
    provider = Mock()
    provider.login = AsyncMock(
        return_value=LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 성공"]
    get_provider.assert_called_once_with("coupang")
    provider.login.assert_awaited_once_with(root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_login_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.login = AsyncMock(
        return_value=LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    provider.login.assert_awaited_once_with(root_dir=tmp_path, terminal=ANY)


@pytest.mark.anyio
async def test_login_status_coupang_command_prints_status_message_once() -> None:
    provider = Mock()
    provider.status = AsyncMock(
        return_value=StatusResult(
            provider="coupang",
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 상태입니다"]
    get_provider.assert_called_once_with("coupang")
    provider.status.assert_awaited_once_with(root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_login_status_coupang_command_passes_root_dir_to_service(
    tmp_path: Path,
) -> None:
    provider = Mock()
    provider.status = AsyncMock(
        return_value=StatusResult(
            provider="coupang",
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )

    with patch("k_commerce_cli.commands.login.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["login", "status", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    provider.status.assert_awaited_once_with(root_dir=tmp_path, terminal=ANY)


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
    provider = Mock()
    provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그아웃 완료"]
    get_provider.assert_called_once_with("coupang")
    provider.logout.assert_awaited_once_with(root_dir=None, terminal=ANY)


@pytest.mark.anyio
async def test_logout_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    provider = Mock()
    provider.logout = AsyncMock(
        return_value=LogoutResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그아웃 완료",
        )
    )

    with patch("k_commerce_cli.commands.logout.get_provider", return_value=provider) as get_provider:
        result = await RUNNER.invoke(app, ["logout", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    get_provider.assert_called_once_with("coupang")
    provider.logout.assert_awaited_once_with(root_dir=tmp_path, terminal=ANY)
