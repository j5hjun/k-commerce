import json
from pathlib import Path

import pytest

from ._helpers import CREDENTIALS_SOURCE_ROOT, copy_provider_artifact, invoke_login, require_smoke_enabled


@pytest.mark.anyio
@pytest.mark.smoke
async def test_coupang_login_with_credentials_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    session_root = root_dir / "coupang"
    copy_provider_artifact(CREDENTIALS_SOURCE_ROOT, root_dir, "credentials.json")

    result = await invoke_login(root_dir)

    assert result.exit_code == 0
    assert result.stdout.splitlines()[-1] == "쿠팡 로그인 성공"
    assert json.loads((session_root / "session-meta.json").read_text(encoding="utf-8")) == {
        "login_method": "automatic",
    }
