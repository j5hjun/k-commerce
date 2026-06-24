import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.cli import app
from k_commerce_cli.providers import LOGIN_PROVIDERS

from ._helpers import RUNNER, make_session


@pytest.mark.anyio
async def test_login_coupang_command_succeeds_with_manual_login_when_credentials_missing(tmp_path: Path) -> None:
    provider = LOGIN_PROVIDERS["coupang"]
    root_dir = tmp_path
    session_root = root_dir / "coupang"
    session = make_session()

    with (
        patch.object(provider.browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider.browser, "open_login_entry", new=AsyncMock()) as open_login_entry,
        patch.object(provider.browser, "wait_for_manual_login", new=AsyncMock(return_value=True)) as wait_for_manual_login,
        patch.object(provider.browser, "save_session", new=AsyncMock()) as save_session,
        patch.object(provider.browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "쿠팡 로그인을 시작합니다...",
        "브라우저에서 직접 로그인해주세요...",
        "쿠팡 로그인 성공",
    ]
    launch.assert_awaited_once_with(session_root)
    open_login_entry.assert_awaited_once_with(session)
    wait_for_manual_login.assert_awaited_once_with(session)
    save_session.assert_awaited_once_with(session)
    close.assert_awaited_once_with(session)
    assert json.loads((session_root / "session-meta.json").read_text(encoding="utf-8")) == {
        "login_method": "manual",
    }
