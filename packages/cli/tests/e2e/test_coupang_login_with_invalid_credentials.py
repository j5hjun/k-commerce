import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.cli import app
from k_commerce_cli.services.registry import get_provider

from ._helpers import RUNNER, ensure_session_root, make_session


@pytest.mark.anyio
async def test_login_coupang_command_fails_with_invalid_credentials(tmp_path: Path) -> None:
    root_dir = tmp_path
    provider = get_provider("coupang", root_dir=root_dir)
    paths = ensure_session_root(root_dir)
    paths.credentials_path.write_text(
        json.dumps({"email": "wrong@example.com", "password": "wrong-password"}),
        encoding="utf-8",
    )
    session = make_session()

    def provide(*_args, **kwargs):
        terminal = kwargs.get("terminal")
        provider.terminal = terminal
        provider.auth_service.terminal = terminal
        provider.order_service.terminal = terminal
        return provider

    with (
        patch("k_commerce_cli.commands.login.get_provider", side_effect=provide),
        patch.object(provider.browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider.auth_service, "_open_login_entry", new=AsyncMock()) as open_login_entry,
        patch.object(provider.auth_service, "_fill_login_form", new=AsyncMock(return_value=True)) as fill_login_form,
        patch.object(provider.auth_service, "_wait_for_credentials_login", new=AsyncMock(return_value=False)) as wait_for_credentials_login,
        patch.object(provider.auth_service, "_wait_for_session_login", new=AsyncMock(return_value=False)) as wait_for_manual_login,
        patch.object(provider.browser, "save_session", new=AsyncMock()) as save_session,
        patch.object(provider.browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 1
    assert result.stdout.splitlines() == [
        "쿠팡 로그인을 시작합니다...",
        "자동 로그인을 시도합니다...",
        "[warn] 브라우저에서 직접 로그인해주세요...",
    ]
    assert result.output.splitlines()[-1] == "Error: 쿠팡 로그인 실패"
    launch.assert_awaited_once_with(provider.store.paths)
    open_login_entry.assert_awaited_once_with(session)
    fill_login_form.assert_awaited_once_with(session, "wrong@example.com", "wrong-password")
    wait_for_credentials_login.assert_awaited_once_with(session)
    wait_for_manual_login.assert_awaited_once_with(session)
    save_session.assert_not_called()
    close.assert_awaited_once_with(session)
    assert not paths.session_meta_path.exists()
