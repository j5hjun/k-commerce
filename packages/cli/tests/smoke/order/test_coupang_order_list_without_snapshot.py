from pathlib import Path

import pytest

from .._helpers import require_smoke_enabled
from ._helpers import (
    assert_order_snapshot_shape,
    copy_session_artifacts,
    invoke_order_list,
    require_written_order_snapshot,
)

pytestmark = pytest.mark.smoke


def test_coupang_order_list_without_snapshot_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    copy_session_artifacts(root_dir)

    result = invoke_order_list(root_dir)

    assert result.returncode == 0
    assert "쿠팡 주문 수집을 시작합니다..." in result.stdout
    require_written_order_snapshot(root_dir)
    assert_order_snapshot_shape(root_dir, refresh=False)
    assert result.stdout.splitlines()[-1].startswith(("[ok] ", "[warn] "))
