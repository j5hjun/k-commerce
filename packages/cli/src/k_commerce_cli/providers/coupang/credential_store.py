import json
from dataclasses import dataclass
from pathlib import Path

from k_commerce_cli.providers.paths import ProviderPaths


@dataclass(frozen=True)
class CoupangCredentials:
    email: str
    password: str


class CoupangCredentialStore:
    def __init__(
        self,
        paths: ProviderPaths | Path | None = None,
        *,
        provider: str = "coupang",
        root_dir: Path | None = None,
    ):
        if isinstance(paths, ProviderPaths):
            self.paths = paths
        elif isinstance(paths, Path):
            self.paths = ProviderPaths(paths.parent.name, root_dir=paths.parent.parent)
            self.credentials_path = paths
            return
        else:
            self.paths = ProviderPaths(provider, root_dir=root_dir or Path.home() / ".k-commerce")

        self.credentials_path = self.paths.credentials_path

    def load(self) -> CoupangCredentials | None:
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

        return CoupangCredentials(email=email, password=password)
