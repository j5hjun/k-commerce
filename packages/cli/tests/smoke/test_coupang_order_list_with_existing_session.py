import json
from pathlib import Path

import pytest

from ._helpers import (
    LOCAL_PROVIDER_SOURCE_ROOT,
    copy_provider_artifact,
    invoke_login,
    invoke_order_list,
    provider_paths,
    require_smoke_enabled,
)

pytestmark = pytest.mark.smoke


def test_coupang_order_list_without_session_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path

    result = invoke_order_list(root_dir)

    assert result.returncode == 1
    assert result.stdout.splitlines()[-1] == "쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."
    assert result.stderr.splitlines()[-1] == "Error: 쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요."


def test_coupang_order_list_with_session_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path

    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "credentials.json")

    login_result = invoke_login(root_dir)
    assert login_result.returncode == 0
    assert login_result.stdout.splitlines()[-1] == "쿠팡 로그인 성공"

    result = invoke_order_list(root_dir)

    assert result.returncode == 0
    assert result.stdout.strip() != ""

    orders_path = provider_paths(root_dir).orders_path
    assert orders_path.is_file()

    payload = json.loads(orders_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload
    assert all(isinstance(item.get("title"), str) and item["title"].strip() for item in payload)
