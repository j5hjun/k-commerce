from pathlib import Path

import pytest

from k_commerce_cli.services.browser.nodriver import NodriverBrowser
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.registry import get_provider, list_providers


def test_get_provider_returns_coupang_provider_instance() -> None:
    provider = get_provider("coupang")

    assert isinstance(provider, CoupangProvider)


def test_get_provider_applies_overridden_root_dir(tmp_path: Path) -> None:
    provider = get_provider("coupang", root_dir=tmp_path)

    assert provider.store.paths.root_dir == tmp_path
    assert provider.store.base_dir == tmp_path / "coupang"


def test_coupang_provider_initializes_default_browser() -> None:
    provider = CoupangProvider(provider_name="coupang")

    assert isinstance(provider._browser, NodriverBrowser)


def test_get_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported provider: unknown. Supported providers: coupang",
    ):
        get_provider("unknown")


def test_list_providers_includes_builtin_coupang_provider() -> None:
    assert list_providers() == ["coupang"]
