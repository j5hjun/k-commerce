import json
from dataclasses import dataclass
from pathlib import Path

import typer

from k_commerce_cli.types import LoginResult


@dataclass(frozen=True)
class CoupangCredentials:
    email: str
    password: str


class CoupangLoginProvider:
    name = "coupang"
    credentials_path = Path.home() / ".k-commerce" / "coupang" / "credentials.json"

    async def login(self) -> LoginResult:
        typer.secho("\n쿠팡 로그인을 시작합니다...", fg=typer.colors.BLUE)
        self._load_credentials()
        return LoginResult(
            provider=self.name,
            success=False,
            message="쿠팡 async 로그인 흐름은 아직 구현되지 않았습니다.",
        )

    def _load_credentials(self) -> CoupangCredentials | None:
        if not self.credentials_path.exists():
            return None

        data = json.loads(self.credentials_path.read_text(encoding="utf-8"))

        email = data.get("email")
        password = data.get("password")

        if not isinstance(email, str) or not email.strip():
            raise ValueError("Credentials file must contain a non-empty 'email'.")

        if not isinstance(password, str) or not password.strip():
            raise ValueError("Credentials file must contain a non-empty 'password'.")

        return CoupangCredentials(email=email, password=password)
