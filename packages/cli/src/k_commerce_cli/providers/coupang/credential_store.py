import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoupangCredentials:
    email: str
    password: str


class CoupangCredentialStore:
    def __init__(self, credentials_path: Path):
        self.credentials_path = credentials_path

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
