import json
import subprocess
from pathlib import Path

from .._helpers import invoke_cli, provider_paths


def invoke_login(
    root_dir: Path,
    *,
    extra_env: dict[str, str] | None = None,
    timeout_seconds: int = 360,
) -> subprocess.CompletedProcess[str]:
    return invoke_cli(
        ["login", "coupang", "--root-dir", str(root_dir)],
        extra_env=extra_env,
        timeout_seconds=timeout_seconds,
    )


def write_credentials(root_dir: Path, email: str, password: str) -> Path:
    paths = provider_paths(root_dir)
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    credentials_path = paths.credentials_path
    credentials_path.write_text(
        json.dumps({"email": email, "password": password}),
        encoding="utf-8",
    )
    return credentials_path
