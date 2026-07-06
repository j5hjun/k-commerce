from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from asyncclick.testing import CliRunner

from k_commerce_cli.cli import app
from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.providers.coupang.types import (
    CoupangOrderList,
    CoupangOrderListResult,
    CoupangOrderMeta,
    CoupangOrderSummary,
)
from k_commerce_cli.services.tools.types import JSONValue, ToolInvocationResult, ToolRuntimeOptions
from k_commerce_cli.services.types import ListCartResult, ListReviewableResult, ProviderName
from k_commerce_cli.services.types.auth import LoginResult, LogoutResult, StatusResult

RUNNER = CliRunner()
AuthAliasResult = LoginResult | LogoutResult | StatusResult


@dataclass(frozen=True, slots=True)
class ExpectedInvocation:
    tool_name: str
    payload: JSONValue
    root_dir: Path | None = None


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    tool_name: str
    payload: JSONValue
    runtime_options: ToolRuntimeOptions | None


class ToolInvoker:
    def __init__(self, result: ToolInvocationResult) -> None:
        self.result: ToolInvocationResult = result
        self.calls: list[ToolInvocation] = []

    async def __call__(
        self,
        tool_name: str,
        payload: JSONValue,
        *,
        runtime_options: ToolRuntimeOptions | None = None,
    ) -> ToolInvocationResult:
        self.calls.append(ToolInvocation(tool_name, payload, runtime_options))
        return self.result

    def single_call(self) -> ToolInvocation:
        assert len(self.calls) == 1
        return self.calls[0]


def assert_invoked_once(invoker: ToolInvoker, expected: ExpectedInvocation) -> None:
    call = invoker.single_call()
    assert call.tool_name == expected.tool_name
    assert call.payload == expected.payload
    assert call.runtime_options is not None
    assert call.runtime_options.root_dir == expected.root_dir
    assert call.runtime_options.terminal is not None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("command", "tool_name", "tool_result"),
    [
        (
            "login",
            "login",
            LoginResult(
                provider=ProviderName.COUPANG,
                success=True,
                message="쿠팡 로그인 성공",
            ),
        ),
        (
            "status",
            "status",
            StatusResult(
                provider=ProviderName.COUPANG,
                logged_in=True,
                message="쿠팡 로그인 상태입니다",
            ),
        ),
        (
            "logout",
            "logout",
            LogoutResult(
                provider=ProviderName.COUPANG,
                success=True,
                message="쿠팡 로그아웃 완료",
            ),
        ),
    ],
)
async def test_auth_aliases_use_shared_invocation(command: str, tool_name: str, tool_result: AuthAliasResult) -> None:
    invoke_tool = ToolInvoker(tool_result)

    with (
        patch(
            f"k_commerce_cli.commands.{command}.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch(f"k_commerce_cli.commands.{command}.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, [command, "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    assert_invoked_once(invoke_tool, ExpectedInvocation(tool_name, {"provider": "coupang"}))


@pytest.mark.anyio
async def test_status_alias_keeps_root_dir_in_runtime_options(tmp_path: Path) -> None:
    invoke_tool = ToolInvoker(
        StatusResult(
            provider=ProviderName.COUPANG,
            logged_in=True,
            message="쿠팡 로그인 상태입니다",
        )
    )

    with patch("k_commerce_cli.commands.status.invoke_tool", invoke_tool, create=True):
        result = await RUNNER.invoke(app, ["status", "coupang", "--root_dir", str(tmp_path)])

    assert result.exit_code == 0
    assert_invoked_once(invoke_tool, ExpectedInvocation("status", {"provider": "coupang"}, tmp_path))


@pytest.mark.anyio
async def test_cart_alias_uses_shared_invocation() -> None:
    invoke_tool = ToolInvoker(
        ListCartResult(
            provider="coupang",
            success=True,
            message="장바구니 상품 (1건):",
            items=(),
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.cart.common.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch("k_commerce_cli.commands.cart.common.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, ["cart", "coupang"])

    assert result.exit_code == 0
    assert_invoked_once(invoke_tool, ExpectedInvocation("cart_list", {"provider": "coupang"}))


@pytest.mark.anyio
async def test_order_list_alias_uses_shared_invocation() -> None:
    invoke_tool = ToolInvoker(
        CoupangOrderListResult(
            message="주문 수집 완료: 총 1건, 추가 0건, 변경 1건, 삭제 0건",
            payload=CoupangOrderList(
                meta=CoupangOrderMeta(
                    provider=ProviderName.COUPANG,
                    collectedAt="2026-06-28T12:00:00+09:00",
                    years=["2026"],
                    failedPages=[],
                    refresh=False,
                    summary=CoupangOrderSummary(
                        totalOrders=1,
                        addedOrders=0,
                        updatedOrders=1,
                        deletedOrders=0,
                    ),
                ),
                orders=[],
            ),
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.order.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch("k_commerce_cli.commands.order.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, ["order", "list", "coupang"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == []
    assert_invoked_once(
        invoke_tool,
        ExpectedInvocation("order_list", {"provider": "coupang", "refresh": False, "failed_only": False}),
    )


@pytest.mark.anyio
async def test_search_alias_uses_shared_invocation_and_prints_result() -> None:
    invoke_tool = ToolInvoker(
        SearchProductResult(
            provider="coupang",
            success=True,
            message="검색 결과가 없습니다.",
            items=(),
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.search.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch("k_commerce_cli.commands.search.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, ["search", "coupang", "후레이크"])

    assert result.exit_code == 0
    assert "검색 결과가 없습니다." in result.output
    assert_invoked_once(
        invoke_tool,
        ExpectedInvocation(
            "search_products",
            {
                "provider": "coupang",
                "keyword": "후레이크",
                "category": None,
                "sort": "relevance",
                "max_results": 10,
            },
        ),
    )


@pytest.mark.anyio
async def test_review_upload_list_alias_uses_shared_invocation_and_prints_empty_message() -> None:
    invoke_tool = ToolInvoker(
        ListReviewableResult(
            provider=ProviderName.COUPANG,
            success=True,
            message="리뷰 작성 가능 (1건):\n\n    #  배송일        상품명",
            items=(),
        )
    )

    with (
        patch(
            "k_commerce_cli.commands.review.upload.get_provider",
            side_effect=AssertionError("command must not call get_provider directly"),
        ),
        patch("k_commerce_cli.commands.review.upload.invoke_tool", invoke_tool, create=True),
    ):
        result = await RUNNER.invoke(app, ["review", "upload", "coupang", "--list"])

    assert result.exit_code == 0
    assert "리뷰 작성 가능한 상품이 없습니다." in result.output
    assert_invoked_once(invoke_tool, ExpectedInvocation("review_list_reviewable", {"provider": "coupang"}))
