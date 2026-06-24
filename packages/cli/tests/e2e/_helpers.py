from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from asyncclick.testing import CliRunner


RUNNER = CliRunner()


def make_session() -> SimpleNamespace:
    return SimpleNamespace(tab=object())


def ensure_session_root(root_dir: Path) -> Path:
    session_root = root_dir / "coupang"
    session_root.mkdir(parents=True, exist_ok=True)
    return session_root


def ensure_profile_dir(root_dir: Path) -> Path:
    session_root = ensure_session_root(root_dir)
    (session_root / "chrome-profile").mkdir(parents=True, exist_ok=True)
    return session_root


def async_return(value):
    return AsyncMock(return_value=value)
