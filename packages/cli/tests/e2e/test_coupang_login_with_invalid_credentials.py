import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from k_commerce_cli.cli import app
from k_commerce_cli.providers import LOGIN_PROVIDERS
from ._helpers import RUNNER, ensure_session_root, make_session


@pytest.mark.anyio
async def test_login_coupang_command_fails_with_invalid_credentials(tmp_path: Path) -> None:
    provider = LOGIN_PROVIDERS["coupang"]
    root_dir = tmp_path
    session_root = ensure_session_root(root_dir)
    (session_root / "credentials.json").write_text(
        json.dumps({"email": "wrong@example.com", "password": "wrong-password"}),
        encoding="utf-8",
    )
    session = make_session()

    with (
        patch.object(provider.browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider.browser, "open_login_entry", new=AsyncMock()) as open_login_entry,
        patch.object(provider.browser, "fill_login_form", new=AsyncMock(return_value=True)) as fill_login_form,
        patch.object(provider.browser, "wait_for_manual_login", new=AsyncMock(side_effect=[False, False])) as wait_for_manual_login,
        patch.object(provider.browser, "save_session", new=AsyncMock()) as save_session,
        patch.object(provider.browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "쿠팡 로그인을 시작합니다...",
        "자동 로그인을 시도합니다...",
        "브라우저에서 직접 로그인해주세요...",
        "쿠팡 로그인 실패",
    ]
    launch.assert_awaited_once_with(session_root)
    open_login_entry.assert_awaited_once_with(session)
    fill_login_form.assert_awaited_once_with(session, "wrong@example.com", "wrong-password")
    assert wait_for_manual_login.await_count == 2
    save_session.assert_not_called()
    close.assert_awaited_once_with(session)
    assert not (session_root / "session-meta.json").exists()
