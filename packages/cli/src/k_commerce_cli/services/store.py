import shutil
import json

from k_commerce_cli.services.base import Store
from k_commerce_cli.services.models import Credentials
from k_commerce_cli.services.paths import ProviderPaths


class ProviderStore(Store):
    def __init__(self, paths: ProviderPaths):
        self.paths = paths
        self.base_dir = paths.base_dir
        self.profile_dir = paths.profile_dir
        self.cookies_file = paths.cookies_file
        self.credentials_path = paths.credentials_path
        self.session_meta_path = paths.session_meta_path

    def load_credentials(self) -> Credentials | None:
        if not self.credentials_path.exists():
            return None

        try:
            data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Credentials file must contain valid JSON.") from exc

        if not isinstance(data, dict):
            raise ValueError("Credentials file must contain a JSON object.")

        email = data.get("email")
        password = data.get("password")

        if not isinstance(email, str) or not email.strip():
            raise ValueError("Credentials file must contain a non-empty 'email'.")

        if not isinstance(password, str) or not password.strip():
            raise ValueError("Credentials file must contain a non-empty 'password'.")

        return Credentials(email=email, password=password)

    def has_profile(self) -> bool:
        return self.profile_dir.is_dir()

    def has_session(self) -> bool:
        return self.cookies_file.is_file()

    def clear_session(self) -> bool:
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

    def write_session_metadata(self, payload: dict[str, str]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session_meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
