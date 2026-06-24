import pytest
from k_commerce_cli.providers import LOGIN_PROVIDERS

from ._helpers import invoke_login, provider_paths, require_smoke_enabled, write_credentials


@pytest.mark.anyio
@pytest.mark.smoke
async def test_coupang_login_with_invalid_credentials_smoke(tmp_path, monkeypatch) -> None:
    require_smoke_enabled()
    provider = LOGIN_PROVIDERS["coupang"]
    root_dir = tmp_path
    paths = provider_paths(root_dir)
    write_credentials(root_dir, "wrong@example.com", "wrong-password")

    async def fail_login(*args, **kwargs):
        return False

    monkeypatch.setattr(provider.browser, "wait_for_manual_login", fail_login)

    result = await invoke_login(root_dir)

    assert result.exit_code == 0
    assert result.stdout.splitlines()[-1] == "쿠팡 로그인 실패"
    assert not paths.session_meta_path.exists()
