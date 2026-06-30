import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from .._helpers import (
    LOCAL_PROVIDER_SOURCE_ROOT,
    copy_provider_artifact,
    invoke_cli,
    provider_paths,
)


def invoke_order_list(
    root_dir: Path,
    *options: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return invoke_cli(
        ["order", "list", "coupang", *options, "--root-dir", str(root_dir)],
        extra_env=extra_env,
    )


def read_orders(root_dir: Path) -> dict[str, Any]:
    return json.loads(
        provider_paths(root_dir).orders_path.read_text(encoding="utf-8")
    )


def write_orders(root_dir: Path, payload: dict[str, Any]) -> None:
    provider_paths(root_dir).orders_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def copy_session_artifacts(root_dir: Path) -> None:
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "chrome-profile")
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "cookies.dat")


def copy_order_snapshot(root_dir: Path) -> None:
    copy_provider_artifact(LOCAL_PROVIDER_SOURCE_ROOT, root_dir, "orders.json")


def assert_order_snapshot_shape(root_dir: Path, *, refresh: bool) -> dict[str, Any]:
    payload = read_orders(root_dir)
    assert payload["meta"]["provider"] == "coupang"
    assert payload["meta"]["refresh"] is refresh
    assert isinstance(payload["meta"]["years"], list)
    assert isinstance(payload["meta"]["failedPages"], list)
    assert isinstance(payload["orders"], list)
    return payload


def require_written_order_snapshot(root_dir: Path) -> None:
    if not provider_paths(root_dir).orders_path.exists():
        pytest.skip("Coupang order page did not expose visible year tabs.")


def rewrite_failed_pages(
    root_dir: Path,
    failed_pages: list[list[str | int]],
) -> None:
    payload = read_orders(root_dir)
    payload["meta"]["failedPages"] = failed_pages
    payload["meta"]["refresh"] = False
    write_orders(root_dir, payload)


def remove_first_order(root_dir: Path) -> dict[str, Any]:
    payload = read_orders(root_dir)
    if not payload["orders"]:
        pytest.skip("Coupang order snapshot has no orders to remove.")

    removed_order = payload["orders"].pop(0)
    payload["meta"]["refresh"] = False
    write_orders(root_dir, payload)
    return removed_order


def rewrite_first_invoice_status(
    root_dir: Path,
    *,
    status: str = "SMOKE_STATUS_CHANGED",
) -> dict[str, Any]:
    payload = read_orders(root_dir)
    for order in payload["orders"]:
        for delivery_group in order.get("deliveryGroupList", []):
            if "invoiceStatus" in delivery_group:
                delivery_group["invoiceStatus"] = status
                payload["meta"]["refresh"] = False
                write_orders(root_dir, payload)
                return order

    pytest.skip("Coupang order snapshot has no invoiceStatus to rewrite.")
