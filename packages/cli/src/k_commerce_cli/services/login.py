from k_commerce_cli.providers import LOGIN_PROVIDERS
from k_commerce_cli.providers.types import LoginResult


def login(provider: str) -> LoginResult:
    try:
        login_provider = LOGIN_PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc

    return login_provider.login()