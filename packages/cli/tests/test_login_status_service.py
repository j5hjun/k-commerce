import importlib
from pathlib import Path

import pytest

from k_commerce_cli.providers import STATUS_PROVIDERS
from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.services import login_status
from k_commerce_cli.types import StatusResult


class StubStatusProvider:
    name = "stub"

    def __init__(self, result: StatusResult) -> None:
        self.result = result
        self.calls: list[Path | None] = []

    async def login_status(self, root_dir: Path | None = None) -> StatusResult:
        self.calls.append(root_dir)
        return self.result


@pytest.mark.anyio
async def test_login_status_dispatches_to_status_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    expected = StatusResult(
        provider="coupang",
        logged_in=True,
        message="쿠팡 로그인 상태 확인",
    )
    provider = StubStatusProvider(result=expected)
    login_status_module = importlib.import_module("k_commerce_cli.services.login_status")

    monkeypatch.setattr(login_status_module, "STATUS_PROVIDERS", {"coupang": provider})

    result = await login_status("coupang", root_dir=tmp_path)

    assert result == expected
    assert provider.calls == [tmp_path]


@pytest.mark.anyio
async def test_login_status_raises_for_unsupported_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported provider: unknown"):
        await login_status("unknown")


def test_status_providers_registers_builtin_coupang_provider() -> None:
    assert ProviderName.COUPANG in STATUS_PROVIDERS
