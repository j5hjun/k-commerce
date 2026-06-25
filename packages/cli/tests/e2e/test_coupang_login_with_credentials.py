import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.cli import app
from k_commerce_cli.providers.registry import get_provider

from ._helpers import RUNNER, ensure_session_root, make_session


@pytest.mark.anyio
async def test_login_coupang_command_succeeds_with_credentials_file(tmp_path: Path) -> None:
    provider = get_provider("coupang")
    login_provider = provider._login_provider
    root_dir = tmp_path
    paths = ensure_session_root(root_dir)
    paths.credentials_path.write_text(
        json.dumps({"email": "merchant@example.com", "password": "secret"}),
        encoding="utf-8",
    )
    session = make_session()

    with (
        patch("k_commerce_cli.commands.login.get_provider", return_value=provider),
        patch.object(login_provider.browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(login_provider.browser, "open_login_entry", new=AsyncMock()) as open_login_entry,
        patch.object(login_provider.browser, "fill_login_form", new=AsyncMock(return_value=True)) as fill_login_form,
        patch.object(login_provider.browser, "wait_for_manual_login", new=AsyncMock(return_value=True)) as wait_for_manual_login,
        patch.object(login_provider.browser, "save_session", new=AsyncMock()) as save_session,
        patch.object(login_provider.browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "쿠팡 로그인을 시작합니다...",
        "자동 로그인을 시도합니다...",
        "쿠팡 로그인 성공",
    ]
    launch.assert_awaited_once_with(login_provider.store.paths)
    open_login_entry.assert_awaited_once_with(session)
    fill_login_form.assert_awaited_once_with(session, "merchant@example.com", "secret")
    wait_for_manual_login.assert_awaited_once_with(session, poll_count=30)
    save_session.assert_awaited_once_with(session)
    close.assert_awaited_once_with(session)
    assert json.loads(paths.session_meta_path.read_text(encoding="utf-8")) == {
        "login_method": "automatic",
    }
