from pathlib import Path

import pytest

from k_commerce_cli.providers.coupang.logout import CoupangLogoutProvider
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.store import ProviderStore


@pytest.mark.anyio
async def test_logout_clears_saved_session(tmp_path: Path) -> None:
    provider = CoupangLogoutProvider()
    provider.store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    provider.store.profile_dir.mkdir(parents=True)
    provider.store.cookies_file.write_text("cookies", encoding="utf-8")
    provider.store.write_session_metadata({"login_method": "automatic"})

    result = await provider.logout(root_dir=tmp_path)

    assert result.success is True
    assert result.message == "쿠팡 로그아웃 완료"
    assert provider.store.has_session() is False


@pytest.mark.anyio
async def test_logout_succeeds_when_session_is_missing(tmp_path: Path) -> None:
    provider = CoupangLogoutProvider()

    result = await provider.logout(root_dir=tmp_path)

    assert result.success is True
    assert result.message == "저장된 쿠팡 세션이 없습니다"
