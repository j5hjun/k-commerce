import json
import shutil
from pathlib import Path

from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.paths import ProviderPaths


class CoupangSessionStore:
    def __init__(
        self,
        paths: ProviderPaths | None = None,
        *,
        provider: str = ProviderName.COUPANG,
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

    def has_session(self) -> bool:
        return (
            self.has_profile()
            or self.cookies_file.is_file()
            or self.session_meta_path.is_file()
        )

    def clear(self) -> bool:
        removed = False
        if self.profile_dir.is_dir():
            shutil.rmtree(self.profile_dir)
            removed = True
        if self.cookies_file.is_file():
            self.cookies_file.unlink()
            removed = True
        if self.session_meta_path.is_file():
            self.session_meta_path.unlink()
            removed = True
        return removed
