from k_commerce_cli.providers.constants import ProviderName
from k_commerce_cli.providers.coupang.login import CoupangLoginProvider
from k_commerce_cli.providers.coupang.logout import CoupangLogoutProvider
from k_commerce_cli.providers.types import LoginProvider, LogoutProvider

LOGIN_PROVIDERS: dict[str, LoginProvider] = {
    ProviderName.COUPANG: CoupangLoginProvider(),
}

LOGOUT_PROVIDERS: dict[str, LogoutProvider] = {
    ProviderName.COUPANG: CoupangLogoutProvider(),
}
