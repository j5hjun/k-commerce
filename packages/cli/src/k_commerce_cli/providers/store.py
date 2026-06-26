import json
import shutil
from dataclasses import asdict
from dataclasses import dataclass

from k_commerce_cli.providers.paths import ProviderPaths
from k_commerce_cli.types import OrderListEntry


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str


class ProviderStore:
    def __init__(self, paths: ProviderPaths):
        self.paths = paths
        self.base_dir = paths.base_dir
        self.profile_dir = paths.profile_dir
        self.cookies_file = paths.cookies_file
        self.credentials_path = paths.credentials_path
        self.session_meta_path = paths.session_meta_path
        self.orders_path = paths.orders_path

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

    def write_order_cache(self, orders: tuple[OrderListEntry, ...]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.orders_path.write_text(
            json.dumps({"orders": [asdict(order) for order in orders]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_order_cache(self) -> tuple[OrderListEntry, ...]:
        if not self.orders_path.exists():
            return ()

        data = json.loads(self.orders_path.read_text(encoding="utf-8"))
        items = data.get("orders", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return ()

        orders: list[OrderListEntry] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                orders.append(
                    OrderListEntry(
                        order_date=str(item["order_date"]),
                        title=str(item["title"]),
                        quantity=int(item["quantity"]),
                        status=str(item["status"]),
                        product_url=str(item["product_url"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(orders)

    def merge_order_cache(self, new_orders: tuple[OrderListEntry, ...]) -> tuple[OrderListEntry, ...]:
        merged: dict[tuple[str, str, int], OrderListEntry] = {}

        for order in self.load_order_cache():
            merged[(order.order_date, order.title, order.quantity)] = order

        for order in new_orders:
            merged[(order.order_date, order.title, order.quantity)] = order

        ordered_keys: list[tuple[str, str, int]] = []
        seen_keys: set[tuple[str, str, int]] = set()
        for order in new_orders + self.load_order_cache():
            key = (order.order_date, order.title, order.quantity)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ordered_keys.append(key)

        merged_orders = tuple(merged[key] for key in ordered_keys if key in merged)
        self.write_order_cache(merged_orders)
        return merged_orders
