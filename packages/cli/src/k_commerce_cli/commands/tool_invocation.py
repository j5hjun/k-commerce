from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Provider
from k_commerce_cli.services.tools.types import ToolProviderFactory


@dataclass(frozen=True, slots=True)
class CachedProvider:
    provider: str
    root_dir: Path | None
    terminal: Terminal | None
    instance: Provider


@dataclass(slots=True)
class CachedProviderFactory:
    root_dir: Path | None
    provider_factory: ToolProviderFactory
    _cache: list[CachedProvider] = field(default_factory=list)

    def __call__(
        self,
        provider: str,
        root_dir: Path | None = None,
        terminal: Terminal | None = None,
    ) -> Provider:
        effective_root_dir = root_dir if root_dir is not None else self.root_dir
        for cached_provider in self._cache:
            if (
                cached_provider.provider == provider
                and cached_provider.root_dir == effective_root_dir
                and cached_provider.terminal is terminal
            ):
                return cached_provider.instance

        instance = self.provider_factory(
            provider,
            root_dir=effective_root_dir,
            terminal=terminal,
        )
        self._cache.append(
            CachedProvider(
                provider=provider,
                root_dir=effective_root_dir,
                terminal=terminal,
                instance=instance,
            )
        )
        return instance
