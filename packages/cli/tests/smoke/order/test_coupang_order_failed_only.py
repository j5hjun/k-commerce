from pathlib import Path

import pytest

from .._helpers import require_smoke_enabled
from ._helpers import (
    copy_order_snapshot,
    copy_session_artifacts,
    invoke_order_sync,
    read_orders,
    rewrite_failed_pages,
)

pytestmark = pytest.mark.smoke


def test_coupang_order_failed_only_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    copy_session_artifacts(root_dir)
    copy_order_snapshot(root_dir)

    payload = read_orders(root_dir)
    years = payload["meta"].get("years") or ["2099"]
    failed_page = [str(years[0]), 1]
    rewrite_failed_pages(root_dir, [failed_page])

    result = invoke_order_sync(root_dir, "--failed-only")

    assert result.returncode == 0
    assert f"{failed_page[0]}년 {failed_page[1]}페이지 재수집 중..." in result.stdout
    assert result.stdout.splitlines()[-1].startswith(("[ok] ", "[warn] "))

    updated = read_orders(root_dir)
    assert isinstance(updated["meta"]["failedPages"], list)
    assert updated["meta"]["refresh"] is False
    assert isinstance(updated["orders"], list)
