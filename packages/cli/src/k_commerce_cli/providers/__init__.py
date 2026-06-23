from k_commerce_cli.providers.coupang.login import CoupangLoginProvider
from k_commerce_cli.providers.types import LoginProvider

LOGIN_PROVIDERS: dict[str, LoginProvider] = {
    "coupang": CoupangLoginProvider(),
}
