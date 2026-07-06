from __future__ import annotations

import json
from pathlib import Path
from typing import override

import anyio
import pytest
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.services.types import CartQuantityUpdateRequest, CartQuantityUpdateResult

from .tool_runner_support import FakeProvider, ProviderCall, patched_tool_provider, write_cart_update_request

RUNNER = CliRunner()


class HangingProvider(FakeProvider):
    @override
    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        _ = await anyio.Event().wait()
        raise AssertionError("unreachable")


class ProviderTimeoutProvider(FakeProvider):
    @override
    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        raise TimeoutError("provider timed out internally")


class UnexpectedFailureProvider(FakeProvider):
    @override
    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        raise RuntimeError("browser failed at /Users/johjun/.cache/profile with token sk-test-secret")


class ValueFailureProvider(FakeProvider):
    @override
    async def update_cart_quantity(
        self,
        request: CartQuantityUpdateRequest,
    ) -> CartQuantityUpdateResult:
        self.calls.append(ProviderCall("update_cart_quantity", request))
        raise ValueError("provider failed at /Users/johjun/.cache/profile with token sk-test-secret")


@pytest.mark.anyio
async def test_request_file_cart_update_quantity_returns_json_error_when_provider_hangs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a generic request-file cart update whose provider operation never completes.
    request_file = write_cart_update_request(tmp_path)
    hanging_provider = HangingProvider()
    monkeypatch.setattr("k_commerce_cli.commands.tool_runner.TOOL_INVOCATION_TIMEOUT_SECONDS", 0.01)

    with patched_tool_provider(hanging_provider):
        # When: the provider dispatch exceeds the generic runner timeout.
        result = await RUNNER.invoke(app, ["cart_update_quantity", "--request-file", str(request_file)])

    # Then: the CLI exits promptly with structured JSON instead of hanging.
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {
            "type": "tool_timeout",
            "message": "Tool invocation timed out after 0.01 seconds.",
            "tool_name": "cart_update_quantity",
        }
    }
    assert hanging_provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(quantity=3, product_id="p", vendor_item_id="v", item_id="i"),
        )
    ]


@pytest.mark.anyio
async def test_provider_raised_timeout_error_returns_provider_error_json(
    tmp_path: Path,
) -> None:
    # Given: a provider that raises its own timeout before the runner deadline.
    request_file = write_cart_update_request(tmp_path)
    provider = ProviderTimeoutProvider()

    with patched_tool_provider(provider):
        # When: the generic runner invokes the provider.
        result = await RUNNER.invoke(app, ["cart_update_quantity", "--request-file", str(request_file)])

    # Then: the provider failure is not reported as the runner deadline timeout.
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {
            "type": "tool_error",
            "message": "provider timed out internally",
            "tool_name": "cart_update_quantity",
        }
    }
    assert provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(quantity=3, product_id="p", vendor_item_id="v", item_id="i"),
        )
    ]


@pytest.mark.anyio
async def test_unexpected_provider_exception_returns_sanitized_tool_error_json(
    tmp_path: Path,
) -> None:
    # Given: a provider failure with path-like and token-like details in the exception.
    request_file = write_cart_update_request(tmp_path)
    provider = UnexpectedFailureProvider()

    with patched_tool_provider(provider):
        # When: the generic runner invokes the provider.
        result = await RUNNER.invoke(app, ["cart_update_quantity", "--request-file", str(request_file)])

    # Then: stderr is structured sanitized JSON and raw exception details are not exposed.
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {
            "type": "tool_error",
            "message": "Tool invocation failed.",
            "tool_name": "cart_update_quantity",
        }
    }
    assert "Traceback" not in result.stderr
    assert "/Users/" not in result.stderr
    assert "sk-test-secret" not in result.stderr
    assert "browser failed" not in result.stderr
    assert provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(quantity=3, product_id="p", vendor_item_id="v", item_id="i"),
        )
    ]


@pytest.mark.anyio
async def test_provider_raised_value_error_returns_sanitized_tool_error_json(
    tmp_path: Path,
) -> None:
    # Given: a provider ValueError with path-like and token-like details in the exception.
    request_file = write_cart_update_request(tmp_path)
    provider = ValueFailureProvider()

    with patched_tool_provider(provider):
        # When: the generic runner invokes the provider.
        result = await RUNNER.invoke(app, ["cart_update_quantity", "--request-file", str(request_file)])

    # Then: stderr is structured sanitized JSON and raw exception details are not exposed.
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {
            "type": "tool_error",
            "message": "Tool invocation failed.",
            "tool_name": "cart_update_quantity",
        }
    }
    assert "Traceback" not in result.stderr
    assert "/Users/" not in result.stderr
    assert "sk-test-secret" not in result.stderr
    assert provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(quantity=3, product_id="p", vendor_item_id="v", item_id="i"),
        )
    ]
