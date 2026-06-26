from pathlib import Path

import pytest

from ._helpers import invoke_login, provider_paths, require_smoke_enabled

pytestmark = pytest.mark.smoke


def test_coupang_login_with_malformed_credentials_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    paths = provider_paths(root_dir)
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    paths.credentials_path.write_text("{not-json}", encoding="utf-8")

    result = invoke_login(root_dir)

    assert result.returncode == 2
    assert result.stderr.splitlines()[-1] == "Error: Invalid value: Credentials file must contain valid JSON."
    assert not paths.session_meta_path.exists()
