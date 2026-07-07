from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import anyio

from k_commerce_cli.base import Terminal
from k_commerce_cli.services.base import Browser, BrowserSession, BrowserTab
from k_commerce_cli.services.providers.coupang.result_metadata import (
    BROWSER_CLOSED_ERROR_CODE,
    LOGIN_REQUIRED_METADATA,
    is_browser_closed_error,
    search_metadata,
)
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
                    error_code=LOGIN_REQUIRED_METADATA.error_code,
                    retryable=LOGIN_REQUIRED_METADATA.retryable,
                    next_tools=LOGIN_REQUIRED_METADATA.next_tools,
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
        except RuntimeError as exc:
            if not is_browser_closed_error(exc):
                raise
            return self._emit_search_result(
                self._to_search_result(
                    _SearchBrowserResult(
                        state=BROWSER_CLOSED_ERROR_CODE,
                        message="브라우저가 닫혀 상품 검색을 완료하지 못했습니다.",
                    )
                ),
                print_result=print_result,
            )
        finally:
            await self._close_browser_session()

    def _to_search_result(self, browser_result: _SearchBrowserResult) -> SearchProductResult:
        if browser_result.state != "success":
            message = browser_result.message or "상품 검색에 실패했습니다."
            metadata = search_metadata(browser_result.state)
            return SearchProductResult(
                provider=self.provider_name,
                success=False,
                message=message,
                items=(),
                error_code=metadata.error_code,
                retryable=metadata.retryable,
                next_tools=metadata.next_tools,
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
        if browser_result.message:
            message = f"{browser_result.message}\n{message}"

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
            f"  {'#':>3}  {'상품ID':<14}  {'가격':<12}  {'리뷰':<6}  상품명",
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
        active_tab = self._active_tab(session)
        items: list[_SearchResultItemData] = []
        seen_links: set[str] = set()
        visited_urls: set[str] = set()
        current_url = search_url
        max_pages = max(1, min(20, (max_results + 35) // 36 + 2))

        for page_index in range(max_pages):
            if current_url in visited_urls:
                break
            visited_urls.add(current_url)
            await active_tab.get(current_url)
            await self._sleep_ms(2000)

            if page_index == 0 and not await self._is_logged_in(active_tab):
                return _SearchBrowserResult(
                    state="not_logged_in",
                    message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
                )

            await self._wait_for_search_page_ready(active_tab)
            page_items, _ = await self._scrape_search_results(
                active_tab,
                max_results=max_results - len(items),
            )
            added_count = self._append_unique_search_items(items, page_items, seen_links, max_results)
            if len(items) >= max_results:
                break

            next_url = await self._read_next_search_page_url(active_tab)
            if not next_url or added_count == 0:
                break
            current_url = next_url

        if not items:
            return _SearchBrowserResult(
                state="no_results",
                message="검색 결과를 찾지 못했습니다. 로그인 상태와 검색 페이지 로딩을 확인해주세요.",
            )

        message = None
        if len(items) < max_results:
            message = f"요청한 {max_results}개 중 {len(items)}개만 불러왔습니다"
        return _SearchBrowserResult(state="success", items=tuple(items), message=message)

    def _append_unique_search_items(
        self,
        items: list[_SearchResultItemData],
        page_items: tuple[_SearchResultItemData, ...],
        seen_links: set[str],
        max_results: int,
    ) -> int:
        added_count = 0
        for item in page_items:
            key = item.product_link or item.product_id
            if key in seen_links:
                continue
            seen_links.add(key)
            items.append(item)
            added_count += 1
            if len(items) >= max_results:
                break
        return added_count

    def _build_search_url(self, keyword: str, category: str | None, sort: str, *, page: int = 1) -> str:
        params = {"q": keyword, "page": page}
        sort_value = SEARCH_SORT_MAP.get(sort)
        if sort_value:
            params["sorter"] = sort_value
        if category:
            params["categoryId"] = category
        query = urlencode({k: v for k, v in params.items() if v is not None}, encoding="utf-8", doseq=True)
        return f"{COUPANG_SEARCH_URL}?{query}"

    async def _read_next_search_page_url(self, tab: BrowserTab) -> str:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const currentUrl = new URL(window.location.href);
              const currentPage = Number(currentUrl.searchParams.get('page') || '1');
              const readPage = (href) => {
                try {
                  const page = Number(new URL(href, window.location.href).searchParams.get('page') || '');
                  return Number.isFinite(page) ? page : 0;
                } catch (error) {
                  return 0;
                }
              };
              const paginationRoot = document.querySelector('[class*="Pagination_pagination"]') || document;
              const anchors = Array.from(
                paginationRoot.querySelectorAll('a[href*="page="]')
              ).map((anchor) => ({
                href: anchor.href,
                page: readPage(anchor.href),
                text: (anchor.textContent || '').replace(/\\s+/g, ' ').trim(),
                title: anchor.getAttribute('title') || '',
                className: String(anchor.className || ''),
              })).filter((entry) => entry.href && entry.page > currentPage);

              const explicitNext = anchors.find((entry) =>
                entry.text.includes('다음') ||
                entry.title.includes('다음') ||
                entry.className.includes('Pagination_nextBtn')
              );
              if (explicitNext) return explicitNext.href;

              anchors.sort((left, right) => left.page - right.page);
              return anchors[0]?.href || '';
            })()
            """,
        )
        return str(result or "").strip()

    async def _wait_for_search_page_ready(self, tab: BrowserTab, timeout_ms: int = 20000) -> None:
        elapsed_ms = 0
        step_ms = 500
        while elapsed_ms < timeout_ms:
            ready = await self._evaluate_json(
                tab,
                """
                (() => {
                  const parseJsonLdReady = () => {
                    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
                      try {
                        const data = JSON.parse(script.textContent || '');
                        const list = data?.mainEntity?.itemListElement || data?.itemListElement;
                        if (Array.isArray(list) && list.length) {
                          return true;
                        }
                      } catch (error) {
                      }
                    }
                    return false;
                  };
                  const root = document.querySelector('#product-list');
                  if (parseJsonLdReady()) return true;
                  if (!root) return false;
                  if (root.querySelector('li[class*="ProductUnit_productUnit"]')) return true;
                  if (root.querySelector('[class*="RankMark_rank"]')) return true;
                  if (root.querySelector('a[href*="/vp/products/"]')) return true;
                  return false;
                })()
                """,
            )
            if ready:
                return
            await self._sleep_ms(step_ms)
            elapsed_ms += step_ms

    async def _scrape_search_results(
        self,
        tab: BrowserTab,
        *,
        max_results: int,
    ) -> tuple[tuple[_SearchResultItemData, ...], bool]:
        result = await self._evaluate_json(
            tab,
            rf"""
            (() => {{
              const normalizeText = (text) => (text || '').replace(/\s+/g, ' ').trim();
              const truncateText = (text, maxLength) => Array.from(text || '').slice(0, maxLength).join('');
              const compactText = (text) => normalizeText(text).replace(/\s+/g, '');
              const parsePrices = (text) => {{
                const matches = Array.from(normalizeText(text).matchAll(/([\d,]+)\s*\uC6D0/g));
                return matches
                  .map((match) => Number(match[1].replace(/[^0-9]/g, '')))
                  .filter((value) => Number.isFinite(value) && value >= 1000);
              }};
              const uniqueNumbers = (values) => Array.from(new Set(values));
              const readPrice = (element) => {{
                const customOosRoots = Array.from(
                  element.querySelectorAll('div.custom-oos, div[class*="custom-oos"]')
                );
                const collectPriceEntries = (roots) => {{
                  const orderedNodes = roots.flatMap((root) => Array.from(root.querySelectorAll('div, span, strong, a, del')));
                  const wonNodes = orderedNodes.filter((node) =>
                    normalizeText(node.textContent || '').includes('\uC6D0')
                  );
                  const leafWonNodes = wonNodes.filter((node) =>
                    !wonNodes.some((otherNode) => otherNode !== node && node.contains(otherNode))
                  );
                  const priceEntries = leafWonNodes
                    .filter((node) => !compactText(node.textContent || '').includes('\uC801\uB9BD'))
                    .flatMap((node) =>
                      uniqueNumbers(parsePrices(node.textContent || '')).map((price) => ({{
                          node,
                          price,
                          index: orderedNodes.indexOf(node),
                        }})
                      )
                    );
                  return {{orderedNodes, priceEntries}};
                }};
                let priceRoots = customOosRoots.length ? customOosRoots : [element];
                let {{orderedNodes, priceEntries}} = collectPriceEntries(priceRoots);
                if (!priceEntries.length && customOosRoots.length) {{
                  priceRoots = [element];
                  const fallback = collectPriceEntries(priceRoots);
                  orderedNodes = fallback.orderedNodes;
                  priceEntries = fallback.priceEntries;
                }}
                if (!priceEntries.length) {{
                  return '-';
                }}
                const couponNodes = priceRoots.flatMap((root) => Array.from(root.querySelectorAll('div, span, strong, a')))
                  .filter((node) => {{
                    const text = compactText(node.textContent || '');
                    return text.includes('\uCFE0\uD3F0');
                  }});
                const uniquePriceValues = uniqueNumbers(priceEntries.map((entry) => entry.price));
                if (uniquePriceValues.length === 1) {{
                  return String(uniquePriceValues[0]);
                }}
                let remainingEntries = [...priceEntries];
                if (remainingEntries.length === 1) {{
                  return String(remainingEntries[0].price);
                }}
                if (remainingEntries.length > 1) {{
                  const highestPrice = Math.max(...remainingEntries.map((entry) => entry.price));
                  const highestIndex = remainingEntries.findIndex((entry) => entry.price === highestPrice);
                  if (highestIndex >= 0) {{
                    remainingEntries.splice(highestIndex, 1);
                  }}
                }}
                if (remainingEntries.length > 1 && couponNodes.length) {{
                  const labelIndexes = couponNodes
                    .map((node) => orderedNodes.indexOf(node))
                    .filter((index) => index >= 0);
                  const nearestIndex = remainingEntries
                    .map((entry, index) => {{
                      const distance = labelIndexes.length
                        ? Math.min(...labelIndexes.map((labelIndex) => Math.abs(labelIndex - entry.index)))
                        : Number.POSITIVE_INFINITY;
                      return {{distance, index}};
                    }})
                    .sort((left, right) => left.distance - right.distance || left.index - right.index)[0]?.index;
                  if (nearestIndex !== undefined) {{
                    remainingEntries.splice(nearestIndex, 1);
                  }}
                }}
                while (remainingEntries.length > 1) {{
                  const highestPrice = Math.max(...remainingEntries.map((entry) => entry.price));
                  const highestIndex = remainingEntries.findIndex((entry) => entry.price === highestPrice);
                  if (highestIndex < 0) {{
                    break;
                  }}
                  remainingEntries.splice(highestIndex, 1);
                }}
                return String(remainingEntries[0].price);
              }};
              const readReviewStat = (element) => {{
                const ratingRoot = element.querySelector('[class*="ProductRating_productRating"]');
                if (!ratingRoot) {{
                  const legacyRating = element.querySelector(
                    '[class*="rating"], [class*="Rating"], .rating-total > em, .star-rating, .rating-stars'
                  );
                  return normalizeText(legacyRating?.textContent || '') || '-';
                }}
                const reviewMatch = normalizeText(ratingRoot.textContent || '').match(/\(([0-9,]+)\)/);
                if (reviewMatch) {{
                  return reviewMatch[1];
                }}
                const score = ratingRoot.querySelector('[aria-label]')?.getAttribute('aria-label') || '';
                return score || '-';
              }};
              const buildItemFromElement = (element) => {{
                const linkElement = element.querySelector('a[href*="/vp/products/"]');
                const productLink = linkElement?.href || '';
                const productIdMatch = productLink.match(/\/vp\/products\/(\d+)/);
                const productId = productIdMatch ? productIdMatch[1] : '';
                const titleElement = element.querySelector(
                  '[class*="ProductUnit_productNameV2__"], [class*="ProductUnit_productName__"], div.name, .name, .product-name, .prod-name'
                );
                const productName = truncateText(
                  normalizeText(titleElement?.textContent || linkElement?.textContent || ''),
                  30
                );
                if (!productId || !productName) {{
                  return null;
                }}
                const imageElement = element.querySelector('img');
                return {{
                  product_id: productId,
                  product_name: productName,
                  price: readPrice(element) || '-',
                  rating: readReviewStat(element),
                  image_url: imageElement?.src || imageElement?.dataset?.src || '',
                  product_link: productLink,
                }};
              }};
              const items = [];
              const productList = document.querySelector('#product-list');
              const productRoot = productList || document;
              const rankMarkerEntries = Array.from(
                productRoot.querySelectorAll('div[class*="RankMark_rank"], span[class*="RankMark_rank"], [class*="RankMark_rank"]')
              )
                .map((marker) => {{
                  const className = marker.getAttribute('class') || String(marker.className || '');
                  const rankMatch = className.match(/RankMark_rank(\d+)(?:__|\b|_)?/);
                  const rank = rankMatch ? Number(rankMatch[1]) : Number.NaN;
                  return {{rank, marker}};
                }})
                .filter((entry) => Number.isFinite(entry.rank) && entry.rank >= 1)
                .sort((a, b) => a.rank - b.rank);
              const candidates = [];
              const seenElements = new Set();
              const addCandidate = (element) => {{
                if (!element || seenElements.has(element)) {{
                  return;
                }}
                seenElements.add(element);
                candidates.push(element);
              }};

              for (const element of Array.from(
                productRoot.querySelectorAll('li[class*="ProductUnit_productUnit"], [class*="ProductUnit_productUnit"]')
              )) {{
                addCandidate(element);
              }}

              for (const entry of rankMarkerEntries) {{
                const element =
                  entry.marker.closest('li[class*="ProductUnit_productUnit"], li') ||
                  entry.marker.closest('[class*="ProductUnit_productUnit"]') ||
                  entry.marker.closest('[class*="ProductUnit"]');
                addCandidate(element);
              }}

              for (const element of candidates) {{
                const item = buildItemFromElement(element);
                if (!item) {{
                  continue;
                }}

                items.push(item);

                if (items.length >= {max_results}) {{
                  break;
                }}
              }}
              return {{foundRankMarkers: items.length >= Math.min({max_results}, candidates.length), items}};
            }})()
            """,
        )
        if not isinstance(result, dict):
            return (), False

        found_rank_markers = bool(result.get("foundRankMarkers"))
        raw_items = result.get("items")
        if not isinstance(raw_items, list):
            raw_items = []

        items: list[_SearchResultItemData] = []
        for entry in raw_items:
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
        return tuple(items), found_rank_markers

    async def _evaluate_json(self, tab: BrowserTab, script: str) -> object | None:
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return None

        try:
            result = await evaluate(script)
        except Exception:
            return None

        if getattr(result, "__class__", None) and result.__class__.__name__ == "ExceptionDetails":
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
        await anyio.sleep(timeout_ms / 1000)

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
              return !bodyText.includes('濡쒓렇?몄씠 ?꾩슂');
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
