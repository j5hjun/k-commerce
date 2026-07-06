from pathlib import Path

import pytest

from .._helpers import require_smoke_enabled
from ._helpers import (
    assert_order_snapshot_shape,
    copy_order_snapshot,
    copy_session_artifacts,
    invoke_order_sync,
    read_orders,
    rewrite_failed_pages,
)

pytestmark = pytest.mark.smoke


def test_coupang_order_sync_with_failed_snapshot_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    copy_session_artifacts(root_dir)
    copy_order_snapshot(root_dir)

    payload = read_orders(root_dir)
    years = payload["meta"].get("years") or ["2099"]
    rewrite_failed_pages(root_dir, [[str(years[0]), 1]])

    result = invoke_order_sync(root_dir)

    assert result.returncode == 0
    assert "쿠팡 주문 수집을 시작합니다..." in result.stdout
    assert_order_snapshot_shape(root_dir, refresh=False)
    assert result.stdout.splitlines()[-1].startswith(("[ok] ", "[warn] "))
