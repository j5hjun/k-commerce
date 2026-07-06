from pathlib import Path

import pytest

from .._helpers import require_smoke_enabled
from ._helpers import (
    copy_order_snapshot,
    copy_session_artifacts,
    invoke_order_sync,
    read_orders,
    remove_first_order,
)

pytestmark = pytest.mark.smoke


def test_coupang_order_sync_with_missing_order_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    copy_session_artifacts(root_dir)
    copy_order_snapshot(root_dir)
    removed_order = remove_first_order(root_dir)

    result = invoke_order_sync(root_dir)

    assert result.returncode == 0
    assert "쿠팡 주문 수집을 시작합니다..." in result.stdout
    assert result.stdout.splitlines()[-1].startswith(("[ok] ", "[warn] "))

    updated = read_orders(root_dir)
    assert updated["meta"]["summary"]["addedOrders"] >= 1
    assert any(
        order["orderId"] == removed_order["orderId"] for order in updated["orders"]
    )
