from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.cli import app
from k_commerce_cli.providers import LOGIN_PROVIDERS

from ._helpers import RUNNER, ensure_profile_dir, make_session


@pytest.mark.anyio
async def test_login_coupang_command_succeeds_with_existing_session(tmp_path: Path) -> None:
    provider = LOGIN_PROVIDERS["coupang"]
    root_dir = tmp_path
    session_root = ensure_profile_dir(root_dir)
    session = make_session()

    with (
        patch.object(provider.browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider.browser, "open_home", new=AsyncMock()) as open_home,
        patch.object(provider.browser, "is_logged_in", new=AsyncMock(return_value=True)) as is_logged_in,
        patch.object(provider.browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인을 시작합니다...", "쿠팡 로그인 성공"]
    launch.assert_awaited_once_with(session_root)
    open_home.assert_awaited_once_with(session)
    is_logged_in.assert_awaited_once_with(session.tab)
    close.assert_awaited_once_with(session)
