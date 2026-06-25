from pathlib import Path

from k_commerce_cli.providers import STATUS_PROVIDERS
from k_commerce_cli.types import StatusResult


async def login_status(provider: str, root_dir: Path | None = None) -> StatusResult:
    try:
        status_provider = STATUS_PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider: {provider}") from exc

    return await status_provider.login_status(root_dir=root_dir)
