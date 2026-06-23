import unittest
from unittest.mock import AsyncMock, patch

from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.types import LoginResult


RUNNER = CliRunner()


class CLITests(unittest.IsolatedAsyncioTestCase):
    async def test_login_coupang_command_prints_login_message(self) -> None:
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

        self.assertEqual(result.exit_code, 0)
        self.assertIn("쿠팡 로그인 성공", result.stdout)
        run_login.assert_awaited_once_with("coupang")
