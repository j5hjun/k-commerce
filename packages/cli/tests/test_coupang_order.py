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
    def __init__(self) -> None:
        self.url = "about:blank"
        self.select_map: dict[str, object | None] = {}
        self.select_errors: dict[str, Exception] = {}
        self.evaluate = AsyncMock()

    async def select(self, selector: str, timeout: int = 0):
        if selector in self.select_errors:
            raise self.select_errors[selector]
        return self.select_map.get(selector)


class _DummyOrderElement:
    def __init__(
        self,
        text: str = "",
        *,
        children: list[object] | None = None,
        query_map: dict[str, list[object]] | None = None,
    ) -> None:
        self.text_all = text
        self.children = children or []
        self._query_map = query_map or {}

    async def query_selector_all(self, selector: str):
        return list(self._query_map.get(selector, []))


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
    item = _DummyOrderElement(
        "테스트 상품 3개 배송완료 장바구니 담기",
        query_map={
            "a": [_DummyOrderElement("테스트 상품")],
        },
    )
    group = _DummyOrderElement(
        "2026. 6. 24 주문 주문 상세보기 테스트 상품 3개 배송완료 장바구니 담기",
        query_map={
            'tr, [class*="sc-5a139ee-0"], td': [item],
        },
    )
    order_root = _DummyOrderElement(children=[group])
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = order_root

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].title == "테스트 상품"
    assert orders[0].quantity == 3
    assert orders[0].status == "배송완료"
    tab.evaluate.assert_not_awaited()


@pytest.mark.anyio
async def test_read_visible_orders_filters_blank_titles_and_defaults_quantity() -> None:
    browser = CoupangOrderBrowser()
    blank_item = _DummyOrderElement(
        "장바구니 담기",
        query_map={"a": [_DummyOrderElement("   ")]},
    )
    valid_item = _DummyOrderElement(
        "두번째 상품 배송중 장바구니 담기",
        query_map={"a": [_DummyOrderElement("두번째 상품")]},
    )
    group = _DummyOrderElement(
        "2026. 6. 24 주문 주문 상세보기 두번째 상품 배송중 장바구니 담기",
        query_map={
            'tr, [class*="sc-5a139ee-0"], td': [blank_item, valid_item],
        },
    )
    order_root = _DummyOrderElement(children=[group])
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = order_root

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].title == "두번째 상품"
    assert orders[0].quantity == 1
    assert orders[0].status == "배송중"


@pytest.mark.anyio
async def test_read_visible_orders_rejects_generic_page_sections_without_order_signals() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = _DummyOrderElement(
        children=[
            _DummyOrderElement("마이쿠팡 공지사항"),
            _DummyOrderElement("추천 상품 모음"),
        ]
    )

    orders = await browser.read_visible_orders(tab)

    assert orders == ()


@pytest.mark.anyio
async def test_read_visible_orders_returns_empty_when_order_root_is_missing() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    orders = await browser.read_visible_orders(tab)

    assert orders == ()


@pytest.mark.anyio
async def test_read_order_page_state_reports_logged_out_page() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.url = "https://login.coupang.com/login/login.pang"
    tab.select_map['input[type="password"], input[name="password"], form[action*="login"]'] = object()

    state = await browser.read_order_page_state(tab)

    assert state["ready"] is False
    assert state["has_login_prompt"] is True
    assert state["has_order_signals"] is False


@pytest.mark.anyio
async def test_read_order_page_state_uses_selectors_without_evaluate() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.url = "https://mc.coupang.com/ssr/desktop/order/list"
    tab.select_map['[data-testid*="order"], [class*="my-area-contents"], [class*="my-area-body"], [class*="order"], [id*="order"]'] = object()

    state = await browser.read_order_page_state(tab)

    assert state["url"] == "https://mc.coupang.com/ssr/desktop/order/list"
    assert state["ready"] is True
    assert state["has_login_prompt"] is False
    assert state["has_order_signals"] is True
    tab.evaluate.assert_not_awaited()


@pytest.mark.anyio
async def test_read_visible_orders_rejects_status_only_non_order_sections() -> None:
    browser = CoupangOrderBrowser()
    ignored_item = _DummyOrderElement(
        "배송상품 주문상태 안내 취소 장바구니 담기",
        query_map={"a": [_DummyOrderElement("배송상품 주문상태 안내")]},
    )
    ignored_group = _DummyOrderElement(
        "주문 상세보기 배송상품 주문상태 안내 취소",
        query_map={'tr, [class*="sc-5a139ee-0"], td': [ignored_item]},
    )
    valid_item = _DummyOrderElement(
        "상품명 배송중 장바구니 담기",
        query_map={"a": [_DummyOrderElement("상품명")]},
    )
    valid_group = _DummyOrderElement(
        "2026. 6. 24 주문 주문 상세보기 상품명 배송중 장바구니 담기",
        query_map={'tr, [class*="sc-5a139ee-0"], td': [valid_item]},
    )
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = _DummyOrderElement(
        children=[ignored_group, valid_group]
    )

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].title == "상품명"
