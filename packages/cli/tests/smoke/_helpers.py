import json
import os
import shutil
from pathlib import Path

import pytest
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app


RUNNER = CliRunner()
LOCAL_PROVIDER_SOURCE_ROOT = Path.home() / ".k-commerce"
CHROME_PROFILE_IGNORE_NAMES = {
    "DevToolsActivePort",
    "RunningChromeVersion",
    "SingletonCookie",
    "SingletonLock",
    "SingletonSocket",
}


def require_smoke_enabled() -> None:
    if os.environ.get("RUN_COUPANG_SMOKE") != "1":
        pytest.skip("Set RUN_COUPANG_SMOKE=1 to run real-browser smoke tests.")


async def invoke_login(root_dir: Path):
    return await RUNNER.invoke(app, ["login", "coupang", "--root-dir", str(root_dir)])


def write_credentials(root_dir: Path, email: str, password: str) -> Path:
    session_root = root_dir / "coupang"
    session_root.mkdir(parents=True, exist_ok=True)
    credentials_path = session_root / "credentials.json"
    credentials_path.write_text(
        json.dumps({"email": email, "password": password}),
        encoding="utf-8",
    )
    return credentials_path


def copy_provider_artifact(source_root: Path, destination_root: Path, relative_path: str) -> None:
    source_path = source_root / "coupang" / relative_path
    if not source_path.exists():
        pytest.skip(f"Missing required smoke artifact: {source_path}")

    destination_path = destination_root / "coupang" / relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path.is_dir():
        ignore = None
        if source_path.name == "chrome-profile":
            ignore = shutil.ignore_patterns(*CHROME_PROFILE_IGNORE_NAMES)
        shutil.copytree(source_path, destination_path, dirs_exist_ok=True, ignore=ignore)
    else:
        shutil.copy2(source_path, destination_path)
