import unittest

from typer.testing import CliRunner

from k_commerce_cli.cli import app


RUNNER = CliRunner()


class CLITests(unittest.TestCase):
    def test_login_coupang_command_prints_placeholder_message(self) -> None:
        result = RUNNER.invoke(app, ["login", "coupang"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("login_coupang is not implemented yet", result.stdout)
