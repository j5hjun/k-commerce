import json
from pathlib import Path

import pytest

import k_commerce_cli.providers.coupang as coupang_provider_module
from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.providers.store import Credentials, ProviderStore


def test_exposes_provider_paths(tmp_path: Path) -> None:
    paths = ProviderPaths("coupang", root_dir=tmp_path)
    store = ProviderStore(paths)

    assert store.paths is paths
    assert store.base_dir == tmp_path / "coupang"
    assert store.profile_dir == tmp_path / "coupang" / "chrome-profile"
    assert store.cookies_file == tmp_path / "coupang" / "cookies.dat"
    assert store.credentials_path == tmp_path / "coupang" / "credentials.json"
    assert store.session_meta_path == tmp_path / "coupang" / "session-meta.json"


def test_load_credentials_returns_dataclass_when_file_exists(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.base_dir.mkdir(parents=True)
    store.credentials_path.write_text(
        '{"email":"merchant@example.com","password":"secret"}',
        encoding="utf-8",
    )

    assert store.load_credentials() == Credentials(
        email="merchant@example.com",
        password="secret",
    )


def test_load_credentials_returns_none_when_file_is_missing(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    assert store.load_credentials() is None


def test_load_credentials_raises_for_invalid_json(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.base_dir.mkdir(parents=True)
    store.credentials_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Credentials file must contain valid JSON\\."):
        store.load_credentials()


def test_load_credentials_raises_for_non_object_json(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.base_dir.mkdir(parents=True)
    store.credentials_path.write_text('["merchant@example.com", "secret"]', encoding="utf-8")

    with pytest.raises(ValueError, match="Credentials file must contain a JSON object\\."):
        store.load_credentials()


@pytest.mark.parametrize("payload", [{}, {"email": ""}, {"email": "   "}, {"password": "secret"}])
def test_load_credentials_raises_for_missing_or_empty_email(
    tmp_path: Path,
    payload: dict[str, str],
) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.base_dir.mkdir(parents=True)
    store.credentials_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Credentials file must contain a non-empty 'email'\\.",
    ):
        store.load_credentials()


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "merchant@example.com"},
        {"email": "merchant@example.com", "password": ""},
        {"email": "merchant@example.com", "password": "   "},
    ],
)
def test_load_credentials_raises_for_missing_or_empty_password(
    tmp_path: Path,
    payload: dict[str, str],
) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.base_dir.mkdir(parents=True)
    store.credentials_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Credentials file must contain a non-empty 'password'\\.",
    ):
        store.load_credentials()


def test_write_session_metadata_persists_json(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    store.write_session_metadata({"login_method": "automatic"})

    assert store.session_meta_path.exists()
    assert json.loads(store.session_meta_path.read_text(encoding="utf-8")) == {
        "login_method": "automatic",
    }


def test_has_profile_is_false_when_missing(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    assert store.has_profile() is False


def test_has_session_is_false_when_no_artifacts_exist(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    assert store.has_session() is False


@pytest.mark.parametrize("artifact", ["profile", "cookies", "metadata"])
def test_has_session_is_true_when_any_session_artifact_exists(
    tmp_path: Path,
    artifact: str,
) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    if artifact == "profile":
        store.profile_dir.mkdir(parents=True)
    elif artifact == "cookies":
        store.base_dir.mkdir(parents=True)
        store.cookies_file.write_text("cookies", encoding="utf-8")
    else:
        store.write_session_metadata({"login_method": "automatic"})

    assert store.has_session() is True


def test_clear_session_removes_session_artifacts_but_keeps_credentials(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))
    store.profile_dir.mkdir(parents=True)
    store.cookies_file.write_text("cookies", encoding="utf-8")
    store.write_session_metadata({"login_method": "automatic"})
    store.credentials_path.write_text(
        '{"email":"merchant@example.com","password":"secret"}',
        encoding="utf-8",
    )

    removed = store.clear_session()

    assert removed is True
    assert store.has_session() is False
    assert store.credentials_path.exists()


def test_clear_session_returns_false_when_session_is_missing(tmp_path: Path) -> None:
    store = ProviderStore(ProviderPaths("coupang", root_dir=tmp_path))

    assert store.clear_session() is False


def test_coupang_package_exports_only_provider_types() -> None:
    assert coupang_provider_module.__all__ == [
        "CoupangLoginProvider",
        "CoupangLogoutProvider",
        "CoupangStatusProvider",
    ]
    assert not hasattr(coupang_provider_module, "CoupangCredentials")
