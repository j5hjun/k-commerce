import json
from pathlib import Path

from k_commerce_cli.providers.paths import ProviderPaths


class CoupangSessionStore:
    def __init__(
        self,
        paths: ProviderPaths | None = None,
        *,
        provider: str = "coupang",
        root_dir: Path | None = None,
    ):
        self.paths = paths or ProviderPaths(provider, root_dir=root_dir or Path.home() / ".k-commerce")
        self.base_dir = self.paths.base_dir
        self.profile_dir = self.paths.profile_dir
        self.cookies_file = self.paths.cookies_file
        self.session_meta_path = self.paths.session_meta_path

    def ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def has_profile(self) -> bool:
        return self.profile_dir.is_dir()

    def write_metadata(self, payload: dict[str, str]) -> None:
        self.ensure_dir()
        self.session_meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
