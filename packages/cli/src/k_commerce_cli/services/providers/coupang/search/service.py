from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlencode

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab
from k_commerce_cli.services.store import ProviderStore
from .type import SearchProductResult, SearchResultItem

COUPANG_SEARCH_URL = "https://www.coupang.com/np/search"
SEARCH_SORT_MAP = {
    "relevance": None,
    "latest": "recent",
    "low_price": "priceAsc",
    "high_price": "priceDesc",
    "review": "scoreDesc",
}


@dataclass(frozen=True)
class _SearchResultItemData:
    product_id: str
    product_name: str
    price: str
    rating: str
    image_url: str
    product_link: str


@dataclass(frozen=True)
class _SearchBrowserResult:
    state: str
    items: tuple[_SearchResultItemData, ...] = ()
    message: str | None = None


def deserialize_evaluate_result(value: object) -> object:
    if isinstance(value, dict) and "type" in value and "value" in value:
        typed = str(value["type"])
        inner = value["value"]
        if typed == "object":
            return {
                str(pair[0]): deserialize_evaluate_result(pair[1])
                for pair in inner
                if isinstance(pair, list) and len(pair) == 2
            }
        if typed == "array":
            return [deserialize_evaluate_result(item) for item in inner]
        if typed == "null":
            return None
        if typed in {"string", "number", "boolean"}:
            return inner
        return inner

    if isinstance(value, list):
        if value and all(
            isinstance(item, list) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {item[0]: deserialize_evaluate_result(item[1]) for item in value}
        return [deserialize_evaluate_result(item) for item in value]

    if isinstance(value, dict):
        return {key: deserialize_evaluate_result(item) for key, item in value.items()}

    return value


class CoupangSearchService:
    def __init__(
        self,
        provider_name: str,
        store: ProviderStore,
        browser: Browser,
        terminal: Terminal | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.store = store
        self.browser = browser
        self.terminal = terminal
        self._browser_session: BrowserSession | None = None

    async def search_products(
        self,
        keyword: str,
        *,
        category: str | None = None,
        sort: str = "relevance",
        max_results: int = 10,
        print_result: bool = True,
    ) -> SearchProductResult:
        terminal = self.terminal
        if terminal is not None:
            terminal.info("쿠팡 상품 검색을 시작합니다...")

        if not self.store.has_session():
            return self._emit_search_result(
                SearchProductResult(
                    provider=self.provider_name,
                    success=False,
                    message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                    items=(),
                ),
                print_result=print_result,
            )

        try:
            self._browser_session = await self.browser.launch(self.store.paths)
            browser_result = await self._list_search_results(
                self._browser_session,
                keyword=keyword,
                category=category,
                sort=sort,
                max_results=max_results,
            )
            return self._emit_search_result(
                self._to_search_result(browser_result),
                print_result=print_result,
            )
        finally:
            await self._close_browser_session()

    def _to_search_result(self, browser_result: _SearchBrowserResult) -> SearchProductResult:
        if browser_result.state != "success":
            message = browser_result.message or "상품 검색에 실패했습니다."
            return SearchProductResult(
                provider=self.provider_name,
                success=False,
                message=message,
                items=(),
            )

        items = tuple(
            SearchResultItem(
                index=index,
                product_id=item.product_id,
                product_name=item.product_name,
                price=item.price,
                rating=item.rating,
                image_url=item.image_url,
                product_link=item.product_link,
            )
            for index, item in enumerate(browser_result.items, start=1)
        )

        message = self._format_search_results(items)
        if not items:
            message = "검색 결과가 없습니다."

        return SearchProductResult(
            provider=self.provider_name,
            success=True,
            message=message,
            items=items,
        )

    def _format_search_results(self, items: tuple[SearchResultItem, ...]) -> str:
        if not items:
            return "검색 결과가 없습니다."

        lines = [
            f"검색 결과 ({len(items)}개):",
            "",
            f"  {'#':>3}  {'상품ID':<14}  {'가격':<12}  {'평점':<6}  상품명",
        ]
        for item in items:
            price = item.price or "-"
            rating = item.rating or "-"
            product_name = item.product_name
            if len(product_name) > 60:
                product_name = f"{product_name[:57]}..."
            lines.append(
                f"  {item.index:>3}  {item.product_id:<14}  {price:<12}  {rating:<6}  {product_name}"
            )
        return "\n".join(lines)

    def _emit_search_result(
        self,
        result: SearchProductResult,
        *,
        print_result: bool = True,
    ) -> SearchProductResult:
        terminal = self.terminal
        if print_result and terminal is not None:
            terminal.echo(result.message)
        if not result.success and terminal is not None:
            terminal.abort(result.message)
        return result

    async def _list_search_results(
        self,
        session: BrowserSession,
        *,
        keyword: str,
        category: str | None,
        sort: str,
        max_results: int,
    ) -> _SearchBrowserResult:
        search_url = self._build_search_url(keyword, category, sort)
        await self._open_search_page(session, search_url)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _SearchBrowserResult(
                state="not_logged_in",
                message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
            )

        items = await self._scrape_search_results(active_tab, max_results=max_results)
        return _SearchBrowserResult(state="success", items=items)

    def _build_search_url(self, keyword: str, category: str | None, sort: str) -> str:
        params = {"q": keyword, "page": 1}
        sort_value = SEARCH_SORT_MAP.get(sort)
        if sort_value:
            params["sorter"] = sort_value
        if category:
            params["categoryId"] = category
        query = urlencode({k: v for k, v in params.items() if v is not None}, encoding="utf-8", doseq=True)
        return f"{COUPANG_SEARCH_URL}?{query}"

    async def _open_search_page(self, session: BrowserSession, search_url: str) -> None:
        await session.tab.get(search_url)
        await self._sleep_ms(3500)

    async def _scrape_search_results(
        self,
        tab: BrowserTab,
        *,
        max_results: int,
    ) -> tuple[_SearchResultItemData, ...]:
        result = await self._evaluate_json(
            tab,
            rf"""
            (() => {{
              const normalizeText = (text) => (text || '').replace(/\s+/g, ' ').trim();
              const items = [];
              const candidates = Array.from(document.querySelectorAll(
                'li.search-product, li.baby-product, div.search-product'
              ));

              for (const element of candidates) {{
                const productId =
                  element.dataset.productId ||
                  element.getAttribute('data-product-id') ||
                  '';
                const linkElement =
                  element.querySelector('a.search-product-link, a.prod-link, a');
                const productLink = linkElement?.href || '';
                const titleElement =
                  element.querySelector('div.name, .name, .product-name, .prod-name, a');
                const productName = normalizeText(
                  titleElement?.textContent || linkElement?.textContent || ''
                );
                const priceElement =
                  element.querySelector('strong.price-value, .price-value, .price, .product-price');
                const priceText = normalizeText(priceElement?.textContent || '');
                const price = priceText.replace(/[^0-9]/g, '');
                const ratingElement =
                  element.querySelector('.rating, .rating-total > em, .star-rating, .rating-stars');
                const rating = normalizeText(ratingElement?.textContent || '');
                const imageElement = element.querySelector('img');
                const imageUrl = imageElement?.src || '';

                if (!productId && productLink) {{
                  const match = productLink.match(/productId=(\\d+)/) ||
                    productLink.match(/\\/products?\\/(\\d+)/);
                  if (match) {{
                    productId = match[1];
                  }}
                }}

                if (!productId || !productName) {{
                  continue;
                }}

                items.push({{
                  product_id: productId,
                  product_name: productName,
                  price: price || '-',
                  rating: rating || '-',
                  image_url: imageUrl,
                  product_link: productLink,
                }});

                if (items.length >= {max_results}) {{
                  break;
                }}
              }}
              return items;
            }})()
            """,
        )
        if not isinstance(result, list):
            return ()

        items: list[_SearchResultItemData] = []
        for entry in result:
            if not isinstance(entry, dict):
                continue
            product_id = str(entry.get("product_id") or "").strip()
            product_name = str(entry.get("product_name") or "").strip()
            price = str(entry.get("price") or "").strip()
            rating = str(entry.get("rating") or "").strip()
            image_url = str(entry.get("image_url") or "").strip()
            product_link = str(entry.get("product_link") or "").strip()
            if not product_id or not product_name:
                continue
            items.append(
                _SearchResultItemData(
                    product_id=product_id,
                    product_name=product_name,
                    price=price,
                    rating=rating,
                    image_url=image_url,
                    product_link=product_link,
                )
            )
        return tuple(items)

    async def _evaluate_json(self, tab: BrowserTab, script: str) -> object | None:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return None

        try:
            result = await evaluate(script)
        except Exception:
            return None

        return deserialize_evaluate_result(result)

    async def _close_browser_session(self) -> None:
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    async def _sleep_ms(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)

    async def _is_logged_in(self, tab: BrowserTab) -> bool:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return False

        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const bodyText = document.body?.innerText || '';
              if (window.location.href.includes('login.coupang.com')) {
                return false;
              }
              return !bodyText.includes('로그인이 필요');
            })()
            """,
        )
        return bool(result)

    def _active_tab(self, session: BrowserSession) -> BrowserTab:
        runtime = getattr(session, "browser", None)
        candidates: list[BrowserTab] = []
        if runtime is not None:
            tabs = getattr(runtime, "tabs", None)
            if isinstance(tabs, list):
                candidates.extend(reversed(tabs))
            main_tab = getattr(runtime, "main_tab", None)
            if main_tab is not None:
                candidates.append(main_tab)
        candidates.append(session.tab)

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if "coupang.com" in url:
                return candidate

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if url.startswith(("https://", "http://", "about:blank")):
                return candidate

        for candidate in candidates:
            if hasattr(candidate, "select"):
                return candidate

        return session.tab
