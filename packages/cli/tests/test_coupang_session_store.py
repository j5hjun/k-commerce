import json
from pathlib import Path

from k_commerce_cli.providers.coupang.session_store import CoupangSessionStore


def test_paths_use_provider_directory(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)

    assert store.base_dir == tmp_path / "coupang"
    assert store.profile_dir == tmp_path / "coupang" / "chrome-profile"
    assert store.cookies_file == tmp_path / "coupang" / "cookies.dat"


def test_has_profile_is_false_when_missing(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)

    assert store.has_profile() is False


def test_write_metadata_creates_session_meta_file(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)

    store.write_metadata({"login_method": "automatic"})

    assert store.session_meta_path.exists()
    assert json.loads(store.session_meta_path.read_text(encoding="utf-8")) == {
        "login_method": "automatic",
    }
