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
from k_commerce_cli.types import OrderPageState


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
        class_name: str | None = None,
        role: str | None = None,
        tabindex: str | None = None,
        cursor: str | None = None,
        href: str | None = None,
    ) -> None:
        self.text_all = text
        self.children = children or []
        self._query_map = query_map or {}
        self.class_name = class_name
        self.role = role
        self.tabindex = tabindex
        self.cursor = cursor
        self.href = href

    async def query_selector_all(self, selector: str):
        return list(self._query_map.get(selector, []))

    def get_attribute(self, name: str):
        mapping = {
            "class": self.class_name,
            "role": self.role,
            "tabindex": self.tabindex,
            "href": self.href,
        }
        return mapping.get(name)


class _PaginatedOrderElement(_DummyOrderElement):
    def __init__(self, on_click) -> None:
        super().__init__("다음")
        self._on_click = on_click

    async def click(self) -> None:
        self._on_click()


class _ClickableOrderElement(_DummyOrderElement):
    def __init__(self, text: str, on_click) -> None:
        super().__init__(text)
        self._on_click = on_click

    async def click(self) -> None:
        self._on_click()


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
            "a": [
                _DummyOrderElement(
                    "",
                    href="/ssr/sdp/link?vendorItemId=75478292828&sourceType=MyCoupang_my_orders_list_product_image",
                ),
                _DummyOrderElement(
                    "RDS_LOGO_WOW_TODAY_MD테스트 상품",
                    href="/ssr/sdp/link?vendorItemId=75478292828",
                ),
                _DummyOrderElement(
                    "테스트 상품",
                    href="/ssr/sdp/link?vendorItemId=75478292828&sourceType=MyCoupang_my_orders_list_product_title",
                )
            ],
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
    assert (
        orders[0].product_url
        == "https://www.coupang.com/ssr/sdp/link?vendorItemId=75478292828&sourceType=MyCoupang_my_orders_list_product_title"
    )
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

    assert state == OrderPageState(
        url="https://login.coupang.com/login/login.pang",
        ready=False,
        has_login_prompt=True,
        has_order_signals=False,
        has_empty_state=False,
        has_loading_indicator=False,
    )


@pytest.mark.anyio
async def test_read_order_page_state_uses_selectors_without_evaluate() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.url = "https://mc.coupang.com/ssr/desktop/order/list"
    tab.select_map['[data-testid*="order"], [class*="my-area-contents"], [class*="my-area-body"], [class*="order"], [id*="order"]'] = object()

    state = await browser.read_order_page_state(tab)

    assert state == OrderPageState(
        url="https://mc.coupang.com/ssr/desktop/order/list",
        ready=True,
        has_login_prompt=False,
        has_order_signals=True,
        has_empty_state=False,
        has_loading_indicator=False,
    )
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


@pytest.mark.anyio
async def test_read_all_orders_follows_next_page_until_it_stops() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    def make_item(title: str, status: str) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{title} {status} 장바구니 담기",
            query_map={"a": [_DummyOrderElement(title)]},
        )

    def make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{date} 주문 주문 상세보기 {item.text_all}",
            query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
        )

    page_index = 0
    roots = [
        _DummyOrderElement(children=[make_group("2026. 6. 26", make_item("첫번째 상품", "배송완료"))]),
        _DummyOrderElement(children=[make_group("2026. 6. 25", make_item("두번째 상품", "배송중"))]),
    ]

    def advance_page() -> None:
        nonlocal page_index
        if page_index + 1 < len(roots):
            page_index += 1
            tab.select_map['[class*="my-area-contents"] > div'] = roots[page_index]
            roots[page_index]._query_map["button, a"] = [_PaginatedOrderElement(advance_page)]
        else:
            roots[page_index]._query_map["button, a"] = []

    tab.select_map['[class*="my-area-contents"] > div'] = roots[page_index]
    roots[page_index]._query_map["button, a"] = [_PaginatedOrderElement(advance_page)]

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("첫번째 상품", "두번째 상품")


@pytest.mark.anyio
async def test_read_orders_through_date_stops_after_crossing_cutoff() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    def make_item(title: str, status: str) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{title} {status} 장바구니 담기",
            query_map={"a": [_DummyOrderElement(title)]},
        )

    def make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{date} 주문 주문 상세보기 {item.text_all}",
            query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
        )

    page_index = 0
    roots = [
        _DummyOrderElement(children=[make_group("2026. 6. 27", make_item("새상품", "결제완료"))]),
        _DummyOrderElement(children=[make_group("2026. 6. 24", make_item("진행상품", "배송중"))]),
        _DummyOrderElement(children=[make_group("2026. 6. 23", make_item("이전상품", "배송완료"))]),
    ]

    def advance_page() -> None:
        nonlocal page_index
        if page_index + 1 < len(roots):
            page_index += 1
            tab.select_map['[class*="my-area-contents"] > div'] = roots[page_index]
            roots[page_index]._query_map["button, a"] = [_PaginatedOrderElement(advance_page)]
        else:
            roots[page_index]._query_map["button, a"] = []

    tab.select_map['[class*="my-area-contents"] > div'] = roots[page_index]
    roots[page_index]._query_map["button, a"] = [_PaginatedOrderElement(advance_page)]

    orders = await browser.read_orders_through_date(tab, "2026. 6. 24")

    assert tuple(order.title for order in orders) == ("새상품", "진행상품")


@pytest.mark.anyio
async def test_read_all_orders_collects_all_period_scopes() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    def make_item(title: str, status: str) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{title} {status} 장바구니 담기",
            query_map={"a": [_DummyOrderElement(title)]},
        )

    def make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{date} 주문 주문 상세보기 {item.text_all}",
            query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
        )

    scopes = {
        "최근 6개월": [make_group("2026. 6. 26", make_item("최근상품", "배송완료"))],
        "2025": [make_group("2025. 12. 24", make_item("작년상품", "배송중"))],
    }
    current_scope = "최근 6개월"
    clicked_scopes: list[str] = []

    def render_root() -> _DummyOrderElement:
        controls = [
            _ClickableOrderElement(label, lambda selected=label: select_scope(selected))
            for label in scopes
        ]
        return _DummyOrderElement(
            children=controls + list(scopes[current_scope]),
        )

    def select_scope(scope: str) -> None:
        nonlocal current_scope
        clicked_scopes.append(scope)
        current_scope = scope
        tab.select_map['[class*="my-area-contents"] > div'] = render_root()

    tab.select_map['[class*="my-area-contents"] > div'] = render_root()

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("작년상품",)
    assert clicked_scopes == ["2025"]


@pytest.mark.anyio
async def test_read_all_orders_collects_period_scopes_outside_order_root() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    def make_item(title: str, status: str) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{title} {status} 장바구니 담기",
            query_map={"a": [_DummyOrderElement(title)]},
        )

    def make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{date} 주문 주문 상세보기 {item.text_all}",
            query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
        )

    scopes = {
        "최근 6개월": _DummyOrderElement(
            children=[make_group("2026. 6. 26", make_item("최근상품", "배송완료"))]
        ),
        "2025": _DummyOrderElement(
            children=[make_group("2025. 12. 24", make_item("작년상품", "배송중"))]
        ),
    }
    current_scope = "최근 6개월"
    clicked_scopes: list[str] = []

    def select_scope(scope: str) -> None:
        nonlocal current_scope
        clicked_scopes.append(scope)
        current_scope = scope
        tab.select_map['[class*="my-area-contents"] > div'] = scopes[current_scope]

    scope_root = _DummyOrderElement(
        children=[
            _ClickableOrderElement(label, lambda selected=label: select_scope(selected))
            for label in scopes
        ]
    )
    tab.select_map['[class*="my-area-body"]'] = scope_root
    tab.select_map['[class*="my-area-contents"] > div'] = scopes[current_scope]

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("작년상품",)
    assert clicked_scopes == ["2025"]


@pytest.mark.anyio
async def test_read_all_orders_collects_pointer_div_scopes_without_button_tags() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()

    def make_item(title: str, status: str) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{title} {status} 장바구니 담기",
            query_map={"a": [_DummyOrderElement(title)]},
        )

    def make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
        return _DummyOrderElement(
            f"{date} 주문 주문 상세보기 {item.text_all}",
            query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
        )

    scopes = {
        "최근 6개월": _DummyOrderElement(
            children=[make_group("2026. 6. 26", make_item("최근상품", "배송완료"))]
        ),
        "2025": _DummyOrderElement(
            children=[make_group("2025. 12. 24", make_item("작년상품", "배송중"))]
        ),
    }
    current_scope = "최근 6개월"
    clicked_scopes: list[str] = []

    def select_scope(scope: str) -> None:
        nonlocal current_scope
        clicked_scopes.append(scope)
        current_scope = scope
        tab.select_map['[class*="my-area-contents"] > div'] = scopes[current_scope]

    scope_nodes = [
        _ClickableOrderElement(label, lambda selected=label: select_scope(selected))
        for label in scopes
    ]
    for node in scope_nodes:
        node.cursor = "pointer"

    search_root = _DummyOrderElement(
        "주문한 상품을 검색할 수 있어요!",
        children=[
            _DummyOrderElement(
                children=scope_nodes,
                query_map={"*": scope_nodes},
            )
        ],
        query_map={"*": scope_nodes},
    )

    tab.select_map['input[placeholder*="주문한 상품"]'] = _DummyOrderElement()
    tab.select_map['[class*="my-area-body"]'] = search_root
    tab.select_map['[class*="my-area-contents"] > div'] = scopes[current_scope]

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("작년상품",)
    assert clicked_scopes == ["2025"]
