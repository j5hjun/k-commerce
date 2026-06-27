import json
import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from k_commerce_cli.services.paths import ProviderPaths

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


def invoke_cli(
    args: Sequence[str],
    *,
    extra_env: dict[str, str] | None = None,
    timeout_seconds: int = 360,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["uv", "run", "k-commerce", *args],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=timeout_seconds,
    )


def invoke_login(
    root_dir: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return invoke_cli(
        ["login", "coupang", "--root-dir", str(root_dir)],
        extra_env=extra_env,
    )


def provider_paths(root_dir: Path) -> ProviderPaths:
    return ProviderPaths("coupang", root_dir=root_dir)


def write_credentials(root_dir: Path, email: str, password: str) -> Path:
    paths = provider_paths(root_dir)
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    credentials_path = paths.credentials_path
    credentials_path.write_text(
        json.dumps({"email": email, "password": password}),
        encoding="utf-8",
    )
    return credentials_path


def copy_provider_artifact(source_root: Path, destination_root: Path, relative_path: str) -> None:
    source_path = ProviderPaths("coupang", root_dir=source_root).base_dir / relative_path
    if not source_path.exists():
        pytest.skip(f"Missing required smoke artifact: {source_path}")

    destination_path = provider_paths(destination_root).base_dir / relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path.is_dir():
        ignore = None
        if source_path.name == "chrome-profile":
            ignore = shutil.ignore_patterns(*CHROME_PROFILE_IGNORE_NAMES)
        shutil.copytree(source_path, destination_path, dirs_exist_ok=True, ignore=ignore)
    else:
        shutil.copy2(source_path, destination_path)
