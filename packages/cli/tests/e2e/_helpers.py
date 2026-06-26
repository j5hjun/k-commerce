from pathlib import Path
from types import SimpleNamespace

from asyncclick.testing import CliRunner
from k_commerce_cli.providers.paths import ProviderPaths

RUNNER = CliRunner()


def make_session() -> SimpleNamespace:
    return SimpleNamespace(tab=object())


def provider_paths(root_dir: Path) -> ProviderPaths:
    return ProviderPaths("coupang", root_dir=root_dir)


def ensure_session_root(root_dir: Path) -> ProviderPaths:
    paths = provider_paths(root_dir)
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_profile_dir(root_dir: Path) -> ProviderPaths:
    paths = ensure_session_root(root_dir)
    paths.profile_dir.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_existing_session(root_dir: Path) -> ProviderPaths:
    paths = ensure_session_root(root_dir)
    paths.cookies_file.write_text("cookies", encoding="utf-8")
    return paths
