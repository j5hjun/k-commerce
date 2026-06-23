from pathlib import Path

SESSION_DIR_NAME = ".coupang-session"
STORAGE_STATE_FILE_NAME = "storage-state.json"


def get_session_dir() -> Path:
    return Path.home() / SESSION_DIR_NAME


def get_storage_state_path() -> Path:
    return get_session_dir() / STORAGE_STATE_FILE_NAME


def logout() -> str:
    storage_state_path = get_storage_state_path()

    if not storage_state_path.exists():
        return "저장된 쿠팡 세션이 없습니다."

    storage_state_path.unlink()
    return "쿠팡 세션이 삭제되었습니다. 다음 사용 시 다시 로그인이 필요합니다."
