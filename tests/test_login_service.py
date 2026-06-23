import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from k_commerce_cli.providers import LOGIN_PROVIDERS
from k_commerce_cli.providers.coupang.login import (
    CoupangCredentials,
    CoupangLoginProvider,
)
from k_commerce_cli.services.login import login as run_login
from k_commerce_cli.types import LoginResult


class CoupangLoginProviderTests(unittest.TestCase):
    def test_load_credentials_uses_credential_store(self) -> None:
        provider = CoupangLoginProvider()
        provider.credential_store = Mock()

        provider._load_credentials()

        provider.credential_store.load.assert_called_once_with()

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

    def test_load_credentials_requires_valid_json(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials.json"
            credentials_path.write_text("{", encoding="utf-8")
            provider.credentials_path = credentials_path

            with self.assertRaisesRegex(
                ValueError,
                "Credentials file must contain valid JSON.",
            ):
                provider._load_credentials()

    def test_load_credentials_requires_json_object(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials.json"
            credentials_path.write_text(json.dumps([]), encoding="utf-8")
            provider.credentials_path = credentials_path

            with self.assertRaisesRegex(
                ValueError,
                "Credentials file must contain a JSON object.",
            ):
                provider._load_credentials()


class CoupangLoginProviderBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_login_entry_uses_direct_login_when_available(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()

        await provider._open_login_entry(page)

        page.goto.assert_awaited_once_with("https://login.coupang.com/login/login.pang")
        page.click.assert_not_called()

    async def test_open_login_entry_falls_back_to_home_product_link(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()
        page.goto.side_effect = [PlaywrightError("blocked"), None]

        await provider._open_login_entry(page)

        page.goto.assert_any_call("https://www.coupang.com/")
        page.click.assert_awaited_once_with('a[href^="/vp/products/"]')

    async def test_open_login_entry_reraises_unexpected_errors(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()
        page.goto.side_effect = ValueError("boom")

        with self.assertRaisesRegex(ValueError, "boom"):
            await provider._open_login_entry(page)


class CoupangLoginProviderFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_prints_automatic_progress_without_final_status(self) -> None:
        provider = CoupangLoginProvider()
        credentials = CoupangCredentials(
            email="merchant@example.com",
            password="super-secret",
        )
        provider._load_credentials = Mock(return_value=credentials)
        provider._restore_session = AsyncMock(return_value=None)
        provider._login_with_credentials = AsyncMock(return_value=True)
        provider._wait_for_manual_login = AsyncMock()
        provider._persist_session = AsyncMock()
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            ),
        )
        self.assertIn("쿠팡 로그인을 시작합니다...", stdout.getvalue())
        self.assertIn("자동 로그인을 시도합니다...", stdout.getvalue())
        self.assertNotIn("쿠팡 로그인 성공", stdout.getvalue())

    async def test_login_prints_manual_progress_without_final_status(self) -> None:
        provider = CoupangLoginProvider()
        provider._load_credentials = Mock(return_value=None)
        provider._restore_session = AsyncMock(return_value=None)
        provider._login_with_credentials = AsyncMock()
        provider._wait_for_manual_login = AsyncMock(return_value=True)
        provider._persist_session = AsyncMock()
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            ),
        )
        self.assertIn("브라우저에서 직접 로그인해주세요...", stdout.getvalue())
        self.assertNotIn("쿠팡 로그인 성공", stdout.getvalue())

    async def test_login_persists_automatic_session_after_credential_success(self) -> None:
        provider = CoupangLoginProvider()
        credentials = CoupangCredentials(
            email="merchant@example.com",
            password="super-secret",
        )
        provider._load_credentials = Mock(return_value=credentials)
        provider._restore_session = AsyncMock(return_value=None)
        provider._login_with_credentials = AsyncMock(return_value=True)
        provider._wait_for_manual_login = AsyncMock()
        provider._persist_session = AsyncMock()

        result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            ),
        )
        provider._login_with_credentials.assert_awaited_once_with(credentials)
        provider._wait_for_manual_login.assert_not_called()
        provider._persist_session.assert_awaited_once_with("automatic")

    async def test_login_reuses_verified_session_before_attempting_login(self) -> None:
        provider = CoupangLoginProvider()
        provider._load_credentials = Mock(return_value=None)
        provider._restore_session = AsyncMock(return_value="restored-session")
        provider._verify_session = AsyncMock(return_value=True)
        provider._login_with_credentials = AsyncMock()
        provider._wait_for_manual_login = AsyncMock()

        result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            ),
        )
        provider._verify_session.assert_awaited_once_with("restored-session")
        provider._login_with_credentials.assert_not_called()
        provider._wait_for_manual_login.assert_not_called()

    async def test_login_attempts_credentials_before_manual_fallback(self) -> None:
        provider = CoupangLoginProvider()
        credentials = CoupangCredentials(
            email="merchant@example.com",
            password="super-secret",
        )
        provider._load_credentials = Mock(return_value=credentials)
        provider._restore_session = AsyncMock(return_value=None)
        provider._login_with_credentials = AsyncMock(return_value=False)
        provider._wait_for_manual_login = AsyncMock(return_value=True)
        provider._persist_session = AsyncMock()

        result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=True,
                message="쿠팡 로그인 성공",
            ),
        )
        provider._login_with_credentials.assert_awaited_once_with(credentials)
        provider._wait_for_manual_login.assert_awaited_once_with()
        provider._persist_session.assert_awaited_once_with("manual")

    async def test_login_fails_when_manual_login_times_out(self) -> None:
        provider = CoupangLoginProvider()
        provider._load_credentials = Mock(return_value=None)
        provider._restore_session = AsyncMock(return_value=None)
        provider._login_with_credentials = AsyncMock()
        provider._wait_for_manual_login = AsyncMock(return_value=False)
        provider._persist_session = AsyncMock()

        result = await provider.login()

        self.assertEqual(
            result,
            LoginResult(
                provider="coupang",
                success=False,
                message="쿠팡 로그인 실패",
            ),
        )
        provider._login_with_credentials.assert_not_called()
        provider._wait_for_manual_login.assert_awaited_once_with()
        provider._persist_session.assert_not_called()


class CoupangLoginProviderPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_persist_session_writes_browser_storage_state_and_metadata(self) -> None:
        provider = CoupangLoginProvider()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider.credentials_path = Path(tmpdir) / "credentials.json"
            context = AsyncMock()
            context.storage_state.side_effect = lambda *, path: Path(path).write_text(
                "{}",
                encoding="utf-8",
            )
            provider._browser_session = Mock(context=context)

            await provider._persist_session("automatic")

            self.assertTrue(provider.session_store.has_storage_state())
            context.storage_state.assert_awaited_once_with(
                path=provider.session_store.storage_state_path
            )
            self.assertEqual(
                json.loads(
                    provider.session_store.session_meta_path.read_text(encoding="utf-8")
                ),
                {"login_method": "automatic"},
            )


class CoupangLoginProviderHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_session_checks_home_and_logged_in_dom(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()
        page.url = "https://www.coupang.com/"
        page.query_selector.side_effect = [None, object()]
        session = Mock(page=page)

        result = await provider._verify_session(session)

        self.assertTrue(result)
        page.goto.assert_awaited_once_with("https://www.coupang.com/")

    async def test_login_with_credentials_submits_form_and_verifies_result(self) -> None:
        provider = CoupangLoginProvider()
        credentials = CoupangCredentials(
            email="merchant@example.com",
            password="super-secret",
        )
        page = AsyncMock()
        page.url = "https://www.coupang.com/"
        page.query_selector.side_effect = [None, object()]
        session = Mock(page=page, context=AsyncMock(), browser=AsyncMock(), playwright=AsyncMock())
        provider.browser.launch = AsyncMock(return_value=session)
        provider._open_login_entry = AsyncMock()

        result = await provider._login_with_credentials(credentials)

        self.assertTrue(result)
        provider.browser.launch.assert_awaited_once_with()
        page.fill.assert_any_await(
            'input[name="email"], input#login-email-input',
            "merchant@example.com",
        )
        page.fill.assert_any_await(
            'input[name="password"], input#login-password-input',
            "super-secret",
        )
        page.click.assert_awaited_once_with('button[type="submit"], .login__button')

    async def test_login_with_credentials_returns_false_on_navigation_timeout(self) -> None:
        provider = CoupangLoginProvider()
        credentials = CoupangCredentials(
            email="merchant@example.com",
            password="super-secret",
        )
        page = AsyncMock()
        page.wait_for_url.side_effect = PlaywrightTimeoutError("timeout")
        session = Mock(page=page, context=AsyncMock(), browser=AsyncMock(), playwright=AsyncMock())
        provider.browser.launch = AsyncMock(return_value=session)
        provider._open_login_entry = AsyncMock()

        result = await provider._login_with_credentials(credentials)

        self.assertFalse(result)

    async def test_wait_for_manual_login_uses_existing_browser_session(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()
        page.is_closed = Mock(return_value=False)
        session = Mock(page=page, context=AsyncMock(), browser=AsyncMock(), playwright=AsyncMock())
        provider._browser_session = session
        provider.browser.launch = AsyncMock()
        provider._current_page_is_logged_in = AsyncMock(return_value=True)

        result = await provider._wait_for_manual_login()

        self.assertTrue(result)
        provider.browser.launch.assert_not_called()
        provider._current_page_is_logged_in.assert_awaited_once_with(page)

    async def test_wait_for_manual_login_polls_logged_in_state_outside_login_domain(self) -> None:
        provider = CoupangLoginProvider()
        page = AsyncMock()
        page.url = "https://www.coupang.com/"
        page.is_closed = Mock(return_value=False)
        session = Mock(page=page, context=AsyncMock(), browser=AsyncMock(), playwright=AsyncMock())
        provider._browser_session = session
        provider._current_page_is_logged_in = AsyncMock(side_effect=[False, True])

        result = await provider._wait_for_manual_login()

        self.assertTrue(result)
        self.assertEqual(provider._current_page_is_logged_in.await_count, 2)
        page.wait_for_timeout.assert_awaited()

    async def test_wait_for_manual_login_switches_to_remaining_context_page_when_original_page_closes(self) -> None:
        provider = CoupangLoginProvider()
        closed_page = AsyncMock()
        closed_page.url = "https://www.coupang.com/"
        closed_page.wait_for_timeout.side_effect = PlaywrightError("closed")
        closed_page.is_closed = Mock(return_value=True)

        next_page = AsyncMock()
        next_page.url = "https://www.coupang.com/"
        next_page.is_closed = Mock(return_value=False)

        context = Mock()
        context.pages = [closed_page, next_page]
        session = Mock(page=closed_page, context=context, browser=AsyncMock(), playwright=AsyncMock())
        provider._browser_session = session
        provider._current_page_is_logged_in = AsyncMock(side_effect=[False, True])

        result = await provider._wait_for_manual_login()

        self.assertTrue(result)
        self.assertEqual(provider._current_page_is_logged_in.await_args_list[-1].args[0], next_page)


class ProviderRegistryTests(unittest.TestCase):
    def test_coupang_provider_is_registered(self) -> None:
        provider = LOGIN_PROVIDERS["coupang"]

        self.assertIsInstance(provider, CoupangLoginProvider)


class LoginServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_dispatches_to_provider_async(self) -> None:
        expected = LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        )

        with patch.object(
            LOGIN_PROVIDERS["coupang"],
            "login",
            new=AsyncMock(return_value=expected),
        ) as login_provider:
            result = await run_login("coupang")

        self.assertEqual(result, expected)
        login_provider.assert_awaited_once_with()

    async def test_login_rejects_unsupported_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported provider: unknown"):
            await run_login("unknown")
