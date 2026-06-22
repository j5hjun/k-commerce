from k_commerce_cli.services.login import login as run_login


def login(provider: str) -> str:
    return run_login(provider)
