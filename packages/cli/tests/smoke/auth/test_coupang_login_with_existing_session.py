from pathlib import Path

import pytest

from .._helpers import (
    LOCAL_PROVIDER_SOURCE_ROOT,
    copy_provider_artifact,
    require_smoke_enabled,
)
from ._helpers import invoke_login

pytestmark = pytest.mark.smoke


def test_coupang_login_with_existing_session_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path

    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "chrome-profile")
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "cookies.dat")

    result = invoke_login(
        root_dir,
        extra_env={"K_COMMERCE_MANUAL_LOGIN_POLL_COUNT": "1"},
        timeout_seconds=90,
    )

    if result.returncode != 0 and (
        "브라우저에서 직접 로그인해주세요" in result.stdout
        or "Session with given id not found" in result.stderr
    ):
        pytest.skip("Copied Coupang session is no longer valid.")

    assert result.returncode == 0
    assert result.stdout.splitlines()[-1] == "[ok] 쿠팡 로그인 성공"
