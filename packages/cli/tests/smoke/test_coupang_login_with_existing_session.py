from pathlib import Path

import pytest

from ._helpers import (
    LOCAL_PROVIDER_SOURCE_ROOT,
    copy_provider_artifact,
    invoke_login,
    require_smoke_enabled,
)

pytestmark = pytest.mark.smoke


def test_coupang_login_with_existing_session_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path

    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "chrome-profile")
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "cookies.dat")

    result = invoke_login(root_dir)

    assert result.returncode == 0
    assert result.stdout.splitlines()[-1] == "[ok] 쿠팡 로그인 성공"
