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


def test_has_session_is_false_when_no_artifacts_exist(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)

    assert store.has_session() is False


def test_has_session_is_true_when_profile_exists(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)
    store.profile_dir.mkdir(parents=True)

    assert store.has_session() is True


def test_clear_removes_session_artifacts_but_keeps_credentials(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)
    store.profile_dir.mkdir(parents=True)
    store.cookies_file.write_text("cookies", encoding="utf-8")
    store.write_metadata({"login_method": "automatic"})
    credentials_path = store.paths.credentials_path
    credentials_path.write_text('{"email":"a@b.com","password":"secret"}', encoding="utf-8")

    removed = store.clear()

    assert removed is True
    assert store.has_session() is False
    assert credentials_path.exists()


def test_clear_returns_false_when_session_is_missing(tmp_path: Path) -> None:
    store = CoupangSessionStore(root_dir=tmp_path)

    assert store.clear() is False
