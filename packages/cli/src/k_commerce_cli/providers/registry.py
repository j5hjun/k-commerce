from k_commerce_cli.providers.base import AuthProvider
from k_commerce_cli.providers.coupang import CoupangAuthProvider


_PROVIDER_CLASSES: dict[str, type[AuthProvider]] = {
    CoupangAuthProvider.name.value: CoupangAuthProvider,
}


def get_provider(name: str) -> AuthProvider:
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
