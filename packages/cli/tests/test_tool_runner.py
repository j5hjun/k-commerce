from __future__ import annotations

import json
from pathlib import Path

import pytest
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.services.types import CartQuantityUpdateRequest

from .tool_runner_support import FakeProvider, ProviderCall, patched_tool_provider, write_cart_update_request

RUNNER = CliRunner()


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.mark.anyio
async def test_inline_json_invokes_generic_runner_when_tool_name_is_registered(fake_provider: FakeProvider) -> None:
    # Given: a registered tool name and inline canonical JSON.
    with patched_tool_provider(fake_provider):
        # When: the root CLI receives the generic runner form.
        result = await RUNNER.invoke(app, ["status", '{"provider":"coupang"}'])

    # Then: stdout is pretty JSON and the provider is called without terminal output.
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.startswith("{\n  ")
    assert json.loads(result.stdout) == {
        "provider": "coupang",
        "logged_in": True,
        "message": "쿠팡 로그인 상태입니다",
    }
    assert fake_provider.calls == [ProviderCall("status")]


@pytest.mark.anyio
async def test_request_file_invokes_generic_runner_when_tool_name_is_registered(
    fake_provider: FakeProvider,
    tmp_path: Path,
) -> None:
    # Given: a request file for a non-command canonical tool.
    request_file = write_cart_update_request(tmp_path)

    with patched_tool_provider(fake_provider):
        # When: the root CLI receives the request-file form.
        result = await RUNNER.invoke(app, ["cart_update_quantity", "--request-file", str(request_file)])

    # Then: the dataclass request reaches the provider and stdout is JSON.
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "provider": "coupang",
        "success": True,
        "message": "쿠팡 장바구니 수량 수정 성공",
        "quantity": 3,
        "product_id": "p",
        "vendor_item_id": "v",
        "item_id": "i",
        "notice": "",
    }
    assert fake_provider.calls == [
        ProviderCall(
            "update_cart_quantity",
            CartQuantityUpdateRequest(quantity=3, product_id="p", vendor_item_id="v", item_id="i"),
        )
    ]


@pytest.mark.anyio
async def test_login_status_logout_accept_json_and_request_file_as_generic_runner(
    fake_provider: FakeProvider,
    tmp_path: Path,
) -> None:
    # Given: overlapping command names invoked with generic JSON forms.
    request_file = tmp_path / "provider.json"
    _ = request_file.write_text('{"provider":"coupang"}', encoding="utf-8")

    with patched_tool_provider(fake_provider):
        # When: login/status/logout are invoked as generic tools.
        login_result = await RUNNER.invoke(app, ["login", '{"provider":"coupang"}'])
        status_result = await RUNNER.invoke(app, ["status", "--request-file", str(request_file)])
        logout_result = await RUNNER.invoke(app, ["logout", '{"provider":"coupang"}'])

    # Then: each invocation emits generic JSON and does not use the human alias output.
    assert login_result.exit_code == 0
    assert json.loads(login_result.stdout)["success"] is True
    assert status_result.exit_code == 0
    assert json.loads(status_result.stdout)["logged_in"] is True
    assert logout_result.exit_code == 0
    assert json.loads(logout_result.stdout)["success"] is True
    assert fake_provider.calls == [
        ProviderCall("login"),
        ProviderCall("status"),
        ProviderCall("logout"),
    ]


@pytest.mark.anyio
async def test_malformed_json_returns_json_error() -> None:
    # Given: malformed inline JSON.
    # When: the generic runner receives it.
    result = await RUNNER.invoke(app, ["status", '{"provider":'])

    # Then: it exits non-zero with a JSON error object.
    assert result.exit_code != 0
    assert '"type": "malformed_json"' in result.stderr
    assert "Malformed JSON" in result.stderr


@pytest.mark.anyio
async def test_unknown_canonical_tool_returns_json_error() -> None:
    # Given: an unregistered canonical-looking tool name.
    # When: the generic runner receives it.
    result = await RUNNER.invoke(app, ["unknown_tool", '{"provider":"coupang"}'])

    # Then: root dispatch reaches the JSON runner instead of Click's unknown-command error.
    assert result.exit_code != 0
    assert '"type": "tool_error"' in result.stderr
    assert '"tool_name": "unknown_tool"' in result.stderr
    assert "Unknown tool" in result.stderr


@pytest.mark.anyio
async def test_request_file_conflict_returns_json_error(tmp_path: Path) -> None:
    # Given: both inline JSON and a request file.
    request_file = tmp_path / "provider.json"
    _ = request_file.write_text('{"provider":"coupang"}', encoding="utf-8")

    # When: the generic runner receives conflicting inputs.
    result = await RUNNER.invoke(app, ["status", '{"provider":"coupang"}', "--request-file", str(request_file)])

    # Then: it exits non-zero with a usage conflict JSON error.
    assert result.exit_code != 0
    assert '"type": "usage_conflict"' in result.stderr
    assert "--request-file" in result.stderr


@pytest.mark.anyio
async def test_validation_failure_returns_json_error() -> None:
    # Given: valid JSON that violates the canonical request schema.
    # When: the generic runner invokes shared validation.
    result = await RUNNER.invoke(app, ["status", '{"provider":"coupang","root_dir":"/tmp"}'])

    # Then: it exits non-zero with a JSON validation error.
    assert result.exit_code != 0
    assert '"type": "tool_error"' in result.stderr
    assert '"field": "root_dir"' in result.stderr
