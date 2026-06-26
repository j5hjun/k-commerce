from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock

import pytest

sys.modules.setdefault("nodriver", types.SimpleNamespace(start=AsyncMock()))

from k_commerce_cli.providers.coupang.browser.order import (  # noqa: E402
    COUPANG_ORDER_LIST_URL,
    CoupangOrderBrowser,
)


class _DummyOrderTab:
    def __init__(self, evaluate_result: object) -> None:
        if isinstance(evaluate_result, list) and evaluate_result and all(
            not isinstance(item, dict) for item in evaluate_result
        ):
            self.evaluate = AsyncMock(side_effect=evaluate_result)
        else:
            self.evaluate = AsyncMock(return_value=evaluate_result)


@pytest.mark.anyio
async def test_open_order_list_opens_coupang_order_list_url() -> None:
    browser = CoupangOrderBrowser()
    tab = types.SimpleNamespace(get=AsyncMock())
    session = types.SimpleNamespace(tab=tab)

    await browser.open_order_list(session)

    tab.get.assert_awaited_once_with(COUPANG_ORDER_LIST_URL)


@pytest.mark.anyio
async def test_read_visible_orders_extracts_text_rows() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab(
        [
            {
                "order_id": "1234567890",
                "title": "테스트 상품",
                "quantity": "3",
                "status": "배송완료",
            }
        ]
    )

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].order_id == "1234567890"
    assert orders[0].title == "테스트 상품"
    assert orders[0].quantity == 3
    assert orders[0].status == "배송완료"


@pytest.mark.anyio
async def test_read_visible_orders_filters_blank_titles_and_defaults_quantity() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab(
        [
            {
                "order_id": "1111",
                "title": "   ",
                "quantity": "9",
                "status": "배송완료",
            },
            {
                "order_id": "2222",
                "title": "두번째 상품",
                "status": "배송중",
            },
        ]
    )

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].order_id == "2222"
    assert orders[0].title == "두번째 상품"
    assert orders[0].quantity == 1
    assert orders[0].status == "배송중"


@pytest.mark.anyio
async def test_read_visible_orders_rejects_generic_page_sections_without_order_signals() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab(
        [
            {
                "order_id": "",
                "title": "마이쿠팡 공지사항",
                "quantity": "1",
                "status": "",
            },
            {
                "order_id": "",
                "title": "추천 상품 모음",
                "quantity": "1",
                "status": "",
            },
        ]
    )

    orders = await browser.read_visible_orders(tab)

    assert orders == ()


@pytest.mark.anyio
async def test_read_visible_orders_recovers_from_transient_evaluate_failure() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab(
        [
            RuntimeError("execution context changed"),
            [
                {
                    "order_id": "1234567890",
                    "title": "테스트 상품",
                    "quantity": "2",
                    "status": "배송완료",
                }
            ],
        ]
    )

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].order_id == "1234567890"
    assert orders[0].title == "테스트 상품"
    assert orders[0].quantity == 2
    assert orders[0].status == "배송완료"
    assert tab.evaluate.await_count == 2


@pytest.mark.anyio
async def test_read_order_page_state_reports_logged_out_page() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab(
        {
            "url": "https://login.coupang.com/login/login.pang",
            "ready": False,
            "has_login_prompt": True,
            "has_order_signals": False,
        }
    )

    state = await browser.read_order_page_state(tab)

    assert state["ready"] is False
    assert state["has_login_prompt"] is True
    assert state["has_order_signals"] is False
