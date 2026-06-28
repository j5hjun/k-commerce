from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.providers.coupang.provider import CoupangProvider


_PROVIDER_CLASSES: dict[str, type[CoupangProvider]] = {
    "coupang": CoupangProvider,
}


def get_provider(
    name: str,
    root_dir: Path | None = None,
    terminal: Terminal | None = None,
) -> CoupangProvider:
    try:
        provider_class = _PROVIDER_CLASSES[name]
    except KeyError as exc:
        supported = ", ".join(list_providers())
        raise ValueError(
            f"Unsupported provider: {name}. Supported providers: {supported}"
        ) from exc

    return provider_class(provider_name=name, root_dir=root_dir, terminal=terminal)


def list_providers() -> list[str]:
    return sorted(_PROVIDER_CLASSES.keys())
