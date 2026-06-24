from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from asyncclick.testing import CliRunner
from k_commerce_cli.cli import app
from k_commerce_cli.types import LoginResult

RUNNER = CliRunner()


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
