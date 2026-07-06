import json
import shutil
from typing import Any

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
        self.orders_path = paths.orders_path
        self.cart_path = paths.cart_path
        self.reviews_path = paths.reviews_path

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

    def load_orders(self) -> dict[str, Any] | None:
        if not self.orders_path.exists():
            return None
        return json.loads(self.orders_path.read_text(encoding="utf-8"))

    def write_orders(self, payload: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.orders_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_cart(self) -> dict[str, Any] | None:
        if not self.cart_path.exists():
            return None
        return json.loads(self.cart_path.read_text(encoding="utf-8"))

    def write_cart(self, payload: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cart_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_reviews(self) -> dict[str, Any] | None:
        if not self.reviews_path.exists():
            return None
        return json.loads(self.reviews_path.read_text(encoding="utf-8"))

    def write_reviews(self, payload: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
