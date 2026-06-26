from k_commerce_cli.providers.base import Provider
from k_commerce_cli.providers.coupang import CoupangProvider


_PROVIDER_CLASSES: dict[str, type[Provider]] = {
    CoupangProvider.name.value: CoupangProvider,
}


def get_provider(name: str) -> Provider:
    normalized_name = name.lower().strip()

    try:
        provider_class = _PROVIDER_CLASSES[normalized_name]
    except KeyError as exc:
        supported = ", ".join(list_providers())
        raise ValueError(
            f"Unsupported provider: {name}. Supported providers: {supported}"
        ) from exc

    return provider_class()


def list_providers() -> list[str]:
    return sorted(_PROVIDER_CLASSES.keys())
