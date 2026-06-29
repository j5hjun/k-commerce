from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.cli import app
from k_commerce_cli.services.registry import get_provider

from ._helpers import RUNNER, ensure_existing_session, make_session


@pytest.mark.anyio
async def test_login_coupang_command_succeeds_with_existing_session(tmp_path: Path) -> None:
    root_dir = tmp_path
    provider = get_provider("coupang", root_dir=root_dir)
    paths = ensure_existing_session(root_dir)
    session = make_session()

    def provide(*_args, **kwargs):
        terminal = kwargs.get("terminal")
        provider.terminal = terminal
        provider._auth.terminal = terminal
        return provider

    with (
        patch("k_commerce_cli.commands.login.get_provider", side_effect=provide),
        patch.object(provider._browser, "launch", new=AsyncMock(return_value=session)) as launch,
        patch.object(provider._auth, "_open_home", new=AsyncMock()) as open_home,
        patch.object(provider._auth, "_is_logged_in", new=AsyncMock(return_value=True)) as is_logged_in,
        patch.object(provider._auth, "_open_login_entry", new=AsyncMock()) as open_login_entry,
        patch.object(provider._auth, "_wait_for_session_login", new=AsyncMock()) as wait_for_manual_login,
        patch.object(provider._browser, "close", new=AsyncMock()) as close,
    ):
        result = await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["쿠팡 로그인을 시작합니다...", "쿠팡 로그인 성공"]
    launch.assert_awaited_once_with(provider.store.paths)
    assert provider.store.paths == paths
    open_home.assert_awaited_once_with(session)
    is_logged_in.assert_awaited_once_with(session.tab)
    open_login_entry.assert_not_awaited()
    wait_for_manual_login.assert_not_awaited()
    close.assert_awaited_once_with(session)
