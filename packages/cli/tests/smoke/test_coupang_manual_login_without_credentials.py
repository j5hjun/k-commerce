import json

import pytest

from ._helpers import invoke_login, provider_paths, require_smoke_enabled


@pytest.mark.anyio
@pytest.mark.smoke
async def test_coupang_manual_login_without_credentials_smoke(tmp_path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    paths = provider_paths(root_dir)

    result = await invoke_login(root_dir)

    assert result.exit_code == 0
    assert result.stdout.splitlines()[-1] == "쿠팡 로그인 성공"
    assert json.loads(paths.session_meta_path.read_text(encoding="utf-8")) == {
        "login_method": "manual",
    }
