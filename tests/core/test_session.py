from pathlib import Path

import k_commerce_core.coupang.session as session
from k_commerce_core.coupang.session import logout


def test_logout_deletes_storage_state(monkeypatch, tmp_path: Path) -> None:
    session_dir = tmp_path / ".coupang-session"
    session_dir.mkdir()
    storage_state = session_dir / "storage-state.json"
    storage_state.write_text('{"cookies": []}', encoding="utf-8")

    monkeypatch.setattr(session, "get_session_dir", lambda: session_dir)

    message = logout()

    assert not storage_state.exists()
    assert message == "쿠팡 세션이 삭제되었습니다. 다음 사용 시 다시 로그인이 필요합니다."


def test_logout_when_no_session(monkeypatch, tmp_path: Path) -> None:
    session_dir = tmp_path / ".coupang-session"
    session_dir.mkdir()

    monkeypatch.setattr(session, "get_session_dir", lambda: session_dir)

    message = logout()

    assert message == "저장된 쿠팡 세션이 없습니다."
