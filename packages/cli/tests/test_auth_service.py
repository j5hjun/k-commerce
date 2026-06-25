import importlib
from pathlib import Path

import pytest

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.registry import PROVIDERS
from k_commerce_cli.services.auth import login, logout, status
from k_commerce_cli.types import LoginResult, LogoutResult, StatusResult


class StubAuthProvider:
    name = "stub"

    def __init__(
        self,
        login_result: LoginResult,
        status_result: StatusResult,
        logout_result: LogoutResult,
    ) -> None:
        self.login_result = login_result
        self.status_result = status_result
        self.logout_result = logout_result
        self.login_calls: list[Path | None] = []
        self.status_calls: list[Path | None] = []
        self.logout_calls: list[Path | None] = []

    async def login(self, root_dir: Path | None = None) -> LoginResult:
        self.login_calls.append(root_dir)
        return self.login_result

    async def status(self, root_dir: Path | None = None) -> StatusResult:
        self.status_calls.append(root_dir)
        return self.status_result

    async def logout(self, root_dir: Path | None = None) -> LogoutResult:
        self.logout_calls.append(root_dir)
        return self.logout_result


@pytest.fixture
def stub_provider() -> StubAuthProvider:
    return StubAuthProvider(
        login_result=LoginResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그인 성공",
        ),
        status_result=StatusResult(
            provider="coupang",
            logged_in=True,
            message="쿠팡 로그인 상태 확인",
        ),
        logout_result=LogoutResult(
            provider="coupang",
            success=True,
            message="쿠팡 로그아웃 완료",
        ),
    )


@pytest.mark.anyio
async def test_auth_login_dispatches_to_provider(
    monkeypatch: pytest.MonkeyPatch,
    stub_provider: StubAuthProvider,
    tmp_path: Path,
) -> None:
    auth_module = importlib.import_module("k_commerce_cli.services.auth")
    monkeypatch.setattr(auth_module, "PROVIDERS", {"coupang": stub_provider})

    result = await login("coupang", root_dir=tmp_path)

    assert result == stub_provider.login_result
    assert stub_provider.login_calls == [tmp_path]


@pytest.mark.anyio
async def test_auth_status_dispatches_to_provider(
    monkeypatch: pytest.MonkeyPatch,
    stub_provider: StubAuthProvider,
    tmp_path: Path,
) -> None:
    auth_module = importlib.import_module("k_commerce_cli.services.auth")
    monkeypatch.setattr(auth_module, "PROVIDERS", {"coupang": stub_provider})

    result = await status("coupang", root_dir=tmp_path)

    assert result == stub_provider.status_result
    assert stub_provider.status_calls == [tmp_path]


@pytest.mark.anyio
async def test_auth_logout_dispatches_to_provider(
    monkeypatch: pytest.MonkeyPatch,
    stub_provider: StubAuthProvider,
    tmp_path: Path,
) -> None:
    auth_module = importlib.import_module("k_commerce_cli.services.auth")
    monkeypatch.setattr(auth_module, "PROVIDERS", {"coupang": stub_provider})

    result = await logout("coupang", root_dir=tmp_path)

    assert result == stub_provider.logout_result
    assert stub_provider.logout_calls == [tmp_path]


@pytest.mark.anyio
@pytest.mark.parametrize("action", [login, status, logout])
async def test_auth_actions_raise_for_unsupported_provider(action) -> None:
    with pytest.raises(ValueError, match="Unsupported provider: unknown"):
        await action("unknown")


def test_providers_registers_builtin_coupang_provider() -> None:
    assert ProviderName.COUPANG in PROVIDERS
