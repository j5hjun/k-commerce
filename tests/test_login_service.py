import json
import tempfile
import unittest
from pathlib import Path

from k_commerce_cli.providers import LOGIN_PROVIDERS
from k_commerce_cli.providers.coupang.login import (
    CoupangCredentials,
    CoupangLoginProvider,
)


class CoupangLoginProviderTests(unittest.TestCase):
    def test_load_credentials_returns_none_when_file_is_missing(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider.credentials_path = Path(tmpdir) / "credentials.json"

            self.assertIsNone(provider._load_credentials())

    def test_load_credentials_reads_email_and_password(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials.json"
            credentials_path.write_text(
                json.dumps(
                    {
                        "email": "merchant@example.com",
                        "password": "super-secret",
                    }
                ),
                encoding="utf-8",
            )
            provider.credentials_path = credentials_path

            credentials = provider._load_credentials()

        self.assertEqual(
            credentials,
            CoupangCredentials(
                email="merchant@example.com",
                password="super-secret",
            ),
        )

    def test_load_credentials_requires_non_empty_email(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials.json"
            credentials_path.write_text(
                json.dumps(
                    {
                        "email": "",
                        "password": "super-secret",
                    }
                ),
                encoding="utf-8",
            )
            provider.credentials_path = credentials_path

            with self.assertRaisesRegex(
                ValueError,
                "Credentials file must contain a non-empty 'email'.",
            ):
                provider._load_credentials()

    def test_load_credentials_requires_non_empty_password(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials.json"
            credentials_path.write_text(
                json.dumps(
                    {
                        "email": "merchant@example.com",
                        "password": "   ",
                    }
                ),
                encoding="utf-8",
            )
            provider.credentials_path = credentials_path

            with self.assertRaisesRegex(
                ValueError,
                "Credentials file must contain a non-empty 'password'.",
            ):
                provider._load_credentials()


class ProviderRegistryTests(unittest.TestCase):
    def test_coupang_provider_is_registered(self) -> None:
        provider = LOGIN_PROVIDERS["coupang"]

        self.assertIsInstance(provider, CoupangLoginProvider)
