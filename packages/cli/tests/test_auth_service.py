import pytest

from k_commerce_cli.services.providers.coupang.provider import CoupangProvider
from k_commerce_cli.services.registry import get_provider, list_providers


def test_get_provider_returns_coupang_provider_instance() -> None:
    provider = get_provider("coupang")

    assert isinstance(provider, CoupangProvider)


def test_get_provider_raises_for_unsupported_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported provider: unknown. Supported providers: coupang",
    ):
        get_provider("unknown")


def test_list_providers_includes_builtin_coupang_provider() -> None:
    assert list_providers() == ["coupang"]
