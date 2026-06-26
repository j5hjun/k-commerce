from pathlib import Path

import pytest

from ._helpers import (
    LOCAL_PROVIDER_SOURCE_ROOT,
    copy_provider_artifact,
    invoke_order_list,
    require_smoke_enabled,
)


@pytest.mark.anyio
@pytest.mark.smoke
async def test_coupang_order_list_with_existing_session_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path

    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "chrome-profile")
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "cookies.dat")

    result = await invoke_order_list(root_dir)

    assert result.exit_code == 0
    assert result.stdout.strip() != ""
