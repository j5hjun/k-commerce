from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProviderPaths:
    provider: str
    root_dir: Path = field(default_factory=lambda: Path.home() / ".k-commerce")

    @property
    def base_dir(self) -> Path:
        return self.root_dir / self.provider

    @property
    def profile_dir(self) -> Path:
        return self.base_dir / "chrome-profile"

    @property
    def cookies_file(self) -> Path:
        return self.base_dir / "cookies.dat"

    @property
    def credentials_path(self) -> Path:
        return self.base_dir / "credentials.json"

    @property
    def session_meta_path(self) -> Path:
        return self.base_dir / "session-meta.json"

    @property
    def orders_path(self) -> Path:
        return self.base_dir / "orders.json"
