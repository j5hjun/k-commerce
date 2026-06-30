from pathlib import Path
from typing import Protocol

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, Provider, Store
from k_commerce_cli.services.browser.nodriver import NodriverBrowser
from k_commerce_cli.services.paths import ProviderPaths
from k_commerce_cli.services.store import ProviderStore
from k_commerce_cli.services.types import ProviderName
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider


class ProviderFactory(Protocol):
    def __call__(
        self,
        provider: ProviderName,
        terminal: Terminal | None = None,
        browser: Browser | None = None,
        store: Store | None = None,
    ) -> Provider: ...


_PROVIDER_CLASSES: dict[ProviderName, ProviderFactory] = {
    ProviderName.COUPANG: CoupangProvider,
}


def get_provider(
    provider: str,
    root_dir: Path | None = None,
    terminal: Terminal | None = None,
) -> Provider:
    try:
        provider_key = ProviderName(provider)
    except ValueError as exc:
        supported = ", ".join(list_providers())
        raise ValueError(
            f"Unsupported provider: {provider}. Supported providers: {supported}"
        ) from exc

    path = ProviderPaths(provider_key.value, root_dir=root_dir or Path.home() / ".k-commerce")
    store = ProviderStore(paths=path)
    browser = NodriverBrowser()

    provider_class = _PROVIDER_CLASSES[provider_key]

    return provider_class(
        provider=provider_key,
        store=store,
        browser=browser,
        terminal=terminal,
    )


def list_providers() -> list[str]:
    return sorted(provider.value for provider in _PROVIDER_CLASSES)
