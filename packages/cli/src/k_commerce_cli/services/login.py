def login(provider: str) -> str:
    if provider != "coupang":
        raise ValueError(f"Unsupported provider: {provider}")

    return login_coupang()


def login_coupang() -> str:
    return "login_coupang is not implemented yet"
