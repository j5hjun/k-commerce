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
        self.visited_urls: list[str] = []
        self.on_get = None

    async def select(self, selector: str, timeout: int = 0):
        if selector in self.select_errors:
            raise self.select_errors[selector]
        return self.select_map.get(selector)

    async def get(self, url: str):
        self.url = url
        self.visited_urls.append(url)
        if callable(self.on_get):
            self.on_get(url)


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


class _AttrOnlyOrderElement:
    def __init__(self, **attrs: str) -> None:
        self._attrs = attrs

    def __getattr__(self, name: str):
        return self._attrs.get(name)


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
async def test_read_visible_orders_uses_title_link_for_title_and_product_url() -> None:
    browser = CoupangOrderBrowser()
    item = _DummyOrderElement(
        "스카트 THE보송 오래쓰는 스마트 습기제거제, 300g, 12개 1개 배송완료 장바구니 담기",
        query_map={
            "a": [
                _DummyOrderElement(
                    "",
                    href="/ssr/sdp/link?vendorItemId=75478292828&sourceType=MyCoupang_my_orders_list_product_image",
                ),
                _DummyOrderElement(
                    "RDS_LOGO_WOW_TODAY_MD스카트 THE보송 오래쓰는 스마트 습기제거제, 300g, 12개",
                    href=(
                        "/ssr/sdp/link?vendorItemId=75478292828"
                        "&sourceType=MyCoupang_my_orders_list_product_title"
                    ),
                ),
            ],
        },
    )
    group = _DummyOrderElement(
        "2026. 6. 24 주문 주문 상세보기 스카트 THE보송 오래쓰는 스마트 습기제거제, 300g, 12개 1개 배송완료 장바구니 담기",
        query_map={
            'tr, [class*="sc-5a139ee-0"], td': [item],
        },
    )
    order_root = _DummyOrderElement(children=[group])
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = order_root

    orders = await browser.read_visible_orders(tab)

    assert len(orders) == 1
    assert orders[0].title == "스카트 THE보송 오래쓰는 스마트 습기제거제, 300g, 12개"
    assert (
        orders[0].product_url
        == "https://www.coupang.com/ssr/sdp/link?vendorItemId=75478292828&sourceType=MyCoupang_my_orders_list_product_title"
    )


def test_get_attribute_reads_direct_element_attributes_without_getter() -> None:
    browser = CoupangOrderBrowser()

    assert browser._get_attribute(_AttrOnlyOrderElement(href="/ssr/sdp/link?vendorItemId=1"), "href") == (
        "/ssr/sdp/link?vendorItemId=1"
    )


@pytest.mark.anyio
async def test_read_visible_orders_filters_blank_titles_and_defaults_quantity() -> None:
    browser = CoupangOrderBrowser()
    blank_item = _DummyOrderElement(
        "장바구니 담기",
        query_map={"a": [_DummyOrderElement("   ")]},
    )
    valid_item = _DummyOrderElement(
        "두번째 상품 배송중 장바구니 담기",
        query_map={
            "a": [
                _DummyOrderElement(
                    "두번째 상품",
                    href="/ssr/sdp/link?vendorItemId=2&sourceType=MyCoupang_my_orders_list_product_title",
                )
            ]
        },
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
        query_map={
            "a": [
                _DummyOrderElement(
                    "상품명",
                    href="/ssr/sdp/link?vendorItemId=3&sourceType=MyCoupang_my_orders_list_product_title",
                )
            ]
        },
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


def _make_item(title: str, status: str) -> _DummyOrderElement:
    return _DummyOrderElement(
        f"{title} {status} 장바구니 담기",
        query_map={
            "a": [
                _DummyOrderElement(
                    title,
                    href=f"/ssr/sdp/link?vendorItemId={title}&sourceType=MyCoupang_my_orders_list_product_title",
                )
            ]
        },
    )


def _make_group(date: str, item: _DummyOrderElement) -> _DummyOrderElement:
    return _DummyOrderElement(
        f"{date} 주문 주문 상세보기 {item.text_all}",
        query_map={'tr, [class*="sc-5a139ee-0"], td': [item]},
    )


def _make_page(*groups: _DummyOrderElement, has_next: bool = False) -> _DummyOrderElement:
    controls = [_DummyOrderElement("다음")] if has_next else []
    return _DummyOrderElement(children=[*groups], query_map={"button, a": controls})


@pytest.mark.anyio
async def test_scope_labels_collects_recent_period_and_years_from_order_root() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-contents"] > div'] = _DummyOrderElement(
        children=[
            _DummyOrderElement("최근 6개월", href="/ssr/desktop/order/list"),
            _DummyOrderElement("2026", href="/ssr/desktop/order/list?requestYear=2026"),
            _DummyOrderElement("2025", href="/ssr/desktop/order/list?requestYear=2025"),
            _DummyOrderElement("배송조회", href="/foo"),
        ]
    )

    labels = await browser._scope_labels(tab)

    assert labels == ["최근 6개월", "2026", "2025"]


@pytest.mark.anyio
async def test_scope_labels_collects_scopes_outside_order_root() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    tab.select_map['[class*="my-area-body"]'] = _DummyOrderElement(
        children=[
            _DummyOrderElement("최근 6개월", href="/ssr/desktop/order/list"),
            _DummyOrderElement("2026", href="/ssr/desktop/order/list?requestYear=2026"),
            _DummyOrderElement("2025", href="/ssr/desktop/order/list?requestYear=2025"),
        ]
    )
    tab.select_map['[class*="my-area-contents"] > div'] = _DummyOrderElement()

    labels = await browser._scope_labels(tab)

    assert labels == ["최근 6개월", "2026", "2025"]


@pytest.mark.anyio
async def test_read_all_orders_collects_all_scopes_via_urls() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    initial_root = _DummyOrderElement(
        children=[
            _DummyOrderElement("최근 6개월", href="/ssr/desktop/order/list"),
            _DummyOrderElement("2025", href="/ssr/desktop/order/list?requestYear=2025"),
        ]
    )
    pages = {
        COUPANG_ORDER_LIST_URL: _make_page(
            _make_group("2026. 6. 26", _make_item("최근상품", "배송완료")),
            has_next=False,
        ),
        f"{COUPANG_ORDER_LIST_URL}?requestYear=2025": _make_page(
            _make_group("2025. 12. 24", _make_item("작년상품", "배송중")),
            has_next=False,
        ),
    }

    def on_get(url: str) -> None:
        tab.select_map['[class*="my-area-contents"] > div'] = pages[url]

    tab.on_get = on_get
    tab.select_map['[class*="my-area-contents"] > div'] = initial_root

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("최근상품", "작년상품")
    assert tab.visited_urls == [
        COUPANG_ORDER_LIST_URL,
        f"{COUPANG_ORDER_LIST_URL}?requestYear=2025",
    ]


@pytest.mark.anyio
async def test_read_all_orders_paginates_scope_via_page_index_until_next_disappears() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    initial_root = _DummyOrderElement(
        children=[_DummyOrderElement("2026", href="/ssr/desktop/order/list?requestYear=2026")]
    )
    page_one = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026"
    page_two = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026&pageIndex=1"
    pages = {
        page_one: _make_page(_make_group("2026. 6. 26", _make_item("첫번째 상품", "배송완료")), has_next=True),
        page_two: _make_page(_make_group("2026. 6. 25", _make_item("두번째 상품", "배송중")), has_next=False),
    }

    def on_get(url: str) -> None:
        tab.select_map['[class*="my-area-contents"] > div'] = pages[url]

    tab.on_get = on_get
    tab.select_map['[class*="my-area-contents"] > div'] = initial_root

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("첫번째 상품", "두번째 상품")
    assert tab.visited_urls == [page_one, page_two]


@pytest.mark.anyio
async def test_read_all_orders_stops_when_next_page_repeats_same_orders() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    initial_root = _DummyOrderElement(
        children=[_DummyOrderElement("2026", href="/ssr/desktop/order/list?requestYear=2026")]
    )
    page_one = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026"
    page_two = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026&pageIndex=1"
    repeated_page = _make_page(
        _make_group("2026. 6. 26", _make_item("첫번째 상품", "배송완료")),
        has_next=True,
    )
    pages = {
        page_one: repeated_page,
        page_two: repeated_page,
    }

    def on_get(url: str) -> None:
        tab.select_map['[class*="my-area-contents"] > div'] = pages[url]

    tab.on_get = on_get
    tab.select_map['[class*="my-area-contents"] > div'] = initial_root

    orders = await browser.read_all_orders(tab)

    assert tuple(order.title for order in orders) == ("첫번째 상품",)
    assert tab.visited_urls == [page_one, page_two]


@pytest.mark.anyio
async def test_read_orders_through_date_stops_after_crossing_cutoff() -> None:
    browser = CoupangOrderBrowser()
    tab = _DummyOrderTab()
    initial_root = _DummyOrderElement(
        children=[_DummyOrderElement("2026", href="/ssr/desktop/order/list?requestYear=2026")]
    )
    page_one = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026"
    page_two = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026&pageIndex=1"
    page_three = f"{COUPANG_ORDER_LIST_URL}?requestYear=2026&pageIndex=2"
    pages = {
        page_one: _make_page(_make_group("2026. 6. 27", _make_item("새상품", "결제완료")), has_next=True),
        page_two: _make_page(_make_group("2026. 6. 24", _make_item("진행상품", "배송중")), has_next=True),
        page_three: _make_page(_make_group("2026. 6. 23", _make_item("이전상품", "배송완료")), has_next=False),
    }

    def on_get(url: str) -> None:
        tab.select_map['[class*="my-area-contents"] > div'] = pages[url]

    tab.on_get = on_get
    tab.select_map['[class*="my-area-contents"] > div'] = initial_root

    orders = await browser.read_orders_through_date(tab, "2026. 6. 24")

    assert tuple(order.title for order in orders) == ("새상품", "진행상품")
    assert tab.visited_urls == [page_one, page_two, page_three]
