from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    with patch(
        "k_commerce_cli.cli.run_login",
        new=AsyncMock(
            return_value=LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            )
        ),
    ) as run_login:
        result = await RUNNER.invoke(app, ["login", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 성공"]
    run_login.assert_awaited_once_with("coupang", root_dir=None)


@pytest.mark.anyio
async def test_login_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    with patch(
        "k_commerce_cli.cli.run_login",
        new=AsyncMock(
            return_value=LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            )
        ),
    ) as run_login:
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    run_login.assert_awaited_once_with("coupang", root_dir=tmp_path)


@pytest.mark.anyio
async def test_login_status_coupang_command_prints_status_message_once() -> None:
    with patch(
        "k_commerce_cli.cli.run_status",
        new=AsyncMock(
            return_value=StatusResult(
                provider="coupang",
                logged_in=True,
                message="쿠팡 로그인 상태입니다",
            )
        ),
    ) as run_status:
        result = await RUNNER.invoke(app, ["login", "status", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인 상태입니다"]
    run_status.assert_awaited_once_with("coupang", root_dir=None)


@pytest.mark.anyio
async def test_login_status_coupang_command_passes_root_dir_to_service(
    tmp_path: Path,
) -> None:
    with patch(
        "k_commerce_cli.cli.run_status",
        new=AsyncMock(
            return_value=StatusResult(
                provider="coupang",
                logged_in=True,
                message="쿠팡 로그인 상태입니다",
            )
        ),
    ) as run_status:
        result = await RUNNER.invoke(
            app, ["login", "status", "coupang", "--root-dir", str(tmp_path)]
        )

    assert result.exit_code == 0
    run_status.assert_awaited_once_with("coupang", root_dir=tmp_path)


@pytest.mark.anyio
async def test_login_status_unsupported_provider_uses_bad_parameter() -> None:
    with patch(
        "k_commerce_cli.cli.run_status",
        new=AsyncMock(side_effect=ValueError("Unsupported provider: invalid")),
    ) as run_status:
        result = await RUNNER.invoke(app, ["login", "status", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value: Unsupported provider: invalid" in result.output
    run_status.assert_awaited_once_with("invalid", root_dir=None)


@pytest.mark.anyio
async def test_login_status_missing_provider_shows_parse_error() -> None:
    with patch("k_commerce_cli.cli.run_status", new=AsyncMock()) as run_status:
        result = await RUNNER.invoke(app, ["login", "status"])

    assert result.exit_code == 2
    assert "Missing argument 'PROVIDER'" in result.output
    run_status.assert_not_awaited()


@pytest.mark.anyio
async def test_login_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.cli.run_login", new=AsyncMock()) as run_login:
        result = await RUNNER.invoke(app, ["login", "coupang", "extra"])

    assert result.exit_code == 2
    assert "Got unexpected extra argument (extra)" in result.output
    run_login.assert_not_awaited()


@pytest.mark.anyio
async def test_login_status_coupang_command_rejects_malformed_extra_argument() -> None:
    with patch("k_commerce_cli.cli.run_status", new=AsyncMock()) as run_status:
        result = await RUNNER.invoke(app, ["login", "status", "coupang", "extra"])

    assert result.exit_code == 2
    assert "Got unexpected extra argument (extra)" in result.output
    run_status.assert_not_awaited()


@pytest.mark.anyio
async def test_login_invalid_provider_command_is_rejected_by_parser() -> None:
    with patch(
        "k_commerce_cli.cli.run_login",
        new=AsyncMock(
            side_effect=ValueError("Unsupported provider: invalid")
        ),
    ) as run_login:
        result = await RUNNER.invoke(app, ["login", "invalid"])

    assert result.exit_code == 2
    assert "Invalid value: Unsupported provider: invalid" in result.output
    run_login.assert_awaited_once_with("invalid", root_dir=None)


@pytest.mark.anyio
async def test_logout_coupang_command_prints_logout_message_once() -> None:
    with patch(
        "k_commerce_cli.cli.run_logout",
        new=AsyncMock(
            return_value=LogoutResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그아웃 완료",
            )
        ),
    ) as run_logout:
        result = await RUNNER.invoke(app, ["logout", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그아웃 완료"]
    run_logout.assert_awaited_once_with("coupang", root_dir=None)


@pytest.mark.anyio
async def test_logout_coupang_command_passes_root_dir_to_service(tmp_path: Path) -> None:
    with patch(
        "k_commerce_cli.cli.run_logout",
        new=AsyncMock(
            return_value=LogoutResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그아웃 완료",
            )
        ),
    ) as run_logout:
        result = await RUNNER.invoke(app, ["logout", "coupang", "--root-dir", str(tmp_path)])

    assert result.exit_code == 0
    run_logout.assert_awaited_once_with("coupang", root_dir=tmp_path)
