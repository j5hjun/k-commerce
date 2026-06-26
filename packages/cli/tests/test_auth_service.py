import pytest

from k_commerce_cli.providers.coupang import (
    CoupangAuthProvider,
    CoupangOrderProvider,
    CoupangProvider,
)
from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.registry import get_provider, list_providers


def test_get_provider_returns_coupang_provider_instance() -> None:
    provider = get_provider("coupang")

    assert isinstance(provider, CoupangProvider)
    assert isinstance(provider.auth, CoupangAuthProvider)
    assert isinstance(provider.order, CoupangOrderProvider)


def test_get_provider_normalizes_provider_name() -> None:
    provider = get_provider("  COUPANG  ")

    assert isinstance(provider, CoupangProvider)


def test_get_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported provider: unknown. Supported providers: coupang",
    ):
        get_provider("unknown")


def test_list_providers_includes_builtin_coupang_provider() -> None:
    assert list_providers() == [ProviderName.COUPANG.value]
