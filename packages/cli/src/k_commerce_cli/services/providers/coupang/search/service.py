from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
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
        await self._open_search_page(session, search_url)

        active_tab = self._active_tab(session)
        if not await self._is_logged_in(active_tab):
            return _SearchBrowserResult(
                state="not_logged_in",
                message="쿠팡 로그인 상태가 아닙니다. 먼저 로그인해주세요.",
            )

        items, found_rank_markers = await self._scrape_search_results(
            active_tab,
            max_results=max_results,
        )
        if not found_rank_markers and not items:
            return _SearchBrowserResult(
                state="no_rank_markers",
                message="랭크 마커를 찾지 못했습니다.",
            )

        items = await self._apply_product_detail_prices(session, items)
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

    async def _apply_product_detail_prices(
        self,
        session: BrowserSession,
        items: tuple[_SearchResultItemData, ...],
    ) -> tuple[_SearchResultItemData, ...]:
        priced_items: list[_SearchResultItemData] = []
        for item in items:
            detail_url = f"https://www.coupang.com/vp/products/{item.product_id}"
            try:
                await session.tab.get(detail_url)
                await self._sleep_ms(1200)
                detail_price = await self._read_product_detail_price(session.tab)
            except Exception:
                detail_price = ""

            priced_items.append(
                replace(
                    item,
                    price=detail_price or item.price,
                    product_link=item.product_link or detail_url,
                )
            )

        return tuple(priced_items)

    async def _read_product_detail_price(self, tab: BrowserTab) -> str:
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const normalizeText = (text) => (text || '').replace(/\\s+/g, ' ').trim();
              const parsePrices = (text) => {
                const matches = Array.from(normalizeText(text).matchAll(/([\\d,]+)\\s*\\uC6D0/g));
                return matches
                  .map((match) => Number(match[1].replace(/[^0-9]/g, '')))
                  .filter((value) => Number.isFinite(value) && value > 0);
              };
              const parseDiscountRates = (text) => {
                const matches = Array.from(normalizeText(text).matchAll(/(\\d+)\\s*%/g));
                return matches
                  .map((match) => Number(match[1]))
                  .filter((value) => Number.isFinite(value) && value > 0 && value < 100);
              };
              const hasCouponOnlyKeyword = (node) => {
                const context = normalizeText([
                  node?.textContent || '',
                  node?.parentElement?.textContent || '',
                  node?.closest?.('[class*="coupon"], [class*="Coupon"], [class*="wow"], [class*="Wow"]')?.textContent || '',
                ].join(' '));
                return (
                  context.includes('\\uC640\\uC6B0') ||
                  context.includes('\\uD68C\\uC6D0') ||
                  context.includes('\\uCFE0\\uD3F0')
                );
              };
              const uniqueNumbers = (values) => Array.from(new Set(values));
              const calculatedDiscountCandidates = (basePrice, discountRate) => {
                const raw = basePrice * (100 - discountRate) / 100;
                return uniqueNumbers([
                  Math.round(raw),
                  Math.floor(raw),
                  Math.floor(raw / 10) * 10,
                  Math.round(raw / 10) * 10,
                  Math.floor(raw / 100) * 100,
                  Math.round(raw / 100) * 100,
                ]).filter((value) => Number.isFinite(value) && value > 0);
              };
              const readTwcRegularSalePrice = () => {
                const compact = (text) => normalizeText(text).replace(/\\s+/g, '');
                const twcBoldNodes = Array.from(document.querySelectorAll('[class*="twc-font-bold"]'));
                const regularSaleLabel = twcBoldNodes.find((node) =>
                  compact(node.textContent || '').includes('\\uC77C\\uBC18\\uD560\\uC778\\uAC00')
                );
                if (!regularSaleLabel) return '';

                const orderedNodes = Array.from(
                  document.querySelectorAll('[class*="twc-font-bold"], span, strong, div')
                );
                const labelIndex = orderedNodes.indexOf(regularSaleLabel);
                const followingNodes = orderedNodes.slice(labelIndex >= 0 ? labelIndex + 1 : 0);
                for (const node of followingNodes) {
                  if (hasCouponOnlyKeyword(node)) continue;
                  const prices = parsePrices(node.textContent || '');
                  if (prices.length) {
                    return String(prices.length >= 2 ? Math.min(...prices) : prices[0]);
                  }
                }

                return '';
              };
              const twcRegularSalePrice = readTwcRegularSalePrice();
              if (twcRegularSalePrice) return twcRegularSalePrice;

              const priceRoot =
                document.querySelector('.prod-price') ||
                document.querySelector('[class*="prod-price"]') ||
                document.querySelector('[class*="Price"]') ||
                document.querySelector('#contents') ||
                document.body;
              if (!priceRoot) return '';

              const priceNodes = Array.from(
                priceRoot.querySelectorAll('strong, span, div, del')
              ).filter((node) => parsePrices(node.textContent || '').length);
              const compactPriceNodes = priceNodes.filter((node) => normalizeText(node.textContent || '').length <= 80);
              const nodes = compactPriceNodes.length ? compactPriceNodes : priceNodes;
              const baseNodes = nodes.filter((node) => {
                const className = String(node.className || '');
                const text = normalizeText(node.textContent || '');
                return (
                  node.tagName?.toLowerCase() === 'del' ||
                  className.includes('base') ||
                  className.includes('Base') ||
                  className.includes('origin') ||
                  className.includes('Original') ||
                  text.includes('\\uC815\\uAC00')
                );
              });
              const basePrices = baseNodes.flatMap((node) => parsePrices(node.textContent || ''));
              const originalPrice = basePrices.length
                ? Math.max(...basePrices)
                : Math.max(...nodes.flatMap((node) => parsePrices(node.textContent || '')), 0);
              const discountRate = Math.max(...parseDiscountRates(priceRoot.textContent || ''), 0);
              const regularEntries = nodes
                .filter((node) => !hasCouponOnlyKeyword(node))
                .flatMap((node) => parsePrices(node.textContent || '').map((price) => ({price, node})));
              const couponEntries = nodes
                .filter((node) => hasCouponOnlyKeyword(node))
                .flatMap((node) => parsePrices(node.textContent || '').map((price) => ({price, node})));

              if (originalPrice && discountRate) {
                const expectedPrices = calculatedDiscountCandidates(originalPrice, discountRate);
                const matchedRegular = regularEntries.find((entry) => expectedPrices.includes(entry.price));
                if (matchedRegular) return String(matchedRegular.price);
              }

              const saleSelectors = [
                '.total-price strong',
                '.total-price',
                '[class*="sale"] strong',
                '[class*="Sale"] strong',
                '[class*="priceValue"]',
                '[class*="PriceValue"]',
              ];
              for (const selector of saleSelectors) {
                const selected = Array.from(priceRoot.querySelectorAll(selector))
                  .filter((node) => !hasCouponOnlyKeyword(node))
                  .flatMap((node) => parsePrices(node.textContent || ''));
                if (selected.length) return String(Math.min(...selected));
              }

              if (regularEntries.length) {
                const regularPrices = regularEntries.map((entry) => entry.price);
                const belowOriginal = originalPrice
                  ? regularPrices.filter((price) => price < originalPrice)
                  : regularPrices;
                if (belowOriginal.length) return String(Math.min(...belowOriginal));
                return String(Math.min(...regularPrices));
              }

              if (couponEntries.length) {
                return `\\uCFE0\\uD3F0 \\uD560\\uC778\\uAC00: ${Math.min(...couponEntries.map((entry) => entry.price))}`;
              }

              return '';
            })()
            """,
        )
        return str(result or "").strip()

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
              const readPrice = (element) => {{
                const parsePrices = (text) => {{
                  const matches = Array.from(normalizeText(text).matchAll(/([\d,]+)\s*\uC6D0/g));
                  return matches
                    .map((match) => Number(match[1].replace(/[^0-9]/g, '')))
                    .filter((value) => Number.isFinite(value) && value > 0);
                }};
                const parseDiscountRates = (text) => {{
                  const matches = Array.from(normalizeText(text).matchAll(/(\d+)\s*%/g));
                  return matches
                    .map((match) => Number(match[1]))
                    .filter((value) => Number.isFinite(value) && value > 0 && value < 100);
                }};
                const hasMemberOnlyKeyword = (node) => {{
                  const context = normalizeText([
                    node?.textContent || '',
                    node?.parentElement?.textContent || '',
                  ].join(' '));
                  return (
                    context.includes('\uC640\uC6B0') ||
                    context.includes('\uD68C\uC6D0') ||
                    context.includes('\uCFE0\uD3F0')
                  );
                }};
                const uniqueNumbers = (values) => Array.from(new Set(values));
                const lowestPrice = (nodes, options = {{}}) => {{
                  const excludeMemberOnly = Boolean(options.excludeMemberOnly);
                  const prices = nodes.flatMap((node) => {{
                    if (excludeMemberOnly && hasMemberOnlyKeyword(node)) {{
                      return [];
                    }}
                    return parsePrices(node?.textContent || '');
                  }});
                  if (!prices.length) {{
                    return '';
                  }}
                  return String(Math.min(...prices));
                }};
                const calculatedDiscountCandidates = (basePrice, discountRate) => {{
                  const raw = basePrice * (100 - discountRate) / 100;
                  return uniqueNumbers([
                    Math.round(raw),
                    Math.floor(raw),
                    Math.floor(raw / 10) * 10,
                    Math.round(raw / 10) * 10,
                    Math.floor(raw / 100) * 100,
                    Math.round(raw / 100) * 100,
                  ]).filter((value) => Number.isFinite(value) && value > 0);
                }};
                const customOos = Array.from(
                  element.querySelectorAll('div.custom-oos, div[class*="custom-oos"]')
                ).find((node) => {{
                  const className = String(node.className || '');
                  return (
                    className.includes('custom-oos') &&
                    className.includes('fw-flex') &&
                    className.includes('fw-flex-wrap') &&
                    className.includes('fw-items-center') &&
                    className.includes('fw-gap-y-')
                  );
                }});
                if (customOos) {{
                  const boldPriceDivs = Array.from(customOos.querySelectorAll('div[class*="fw-font-bold"]'));
                  const boldPrices = uniqueNumbers(
                    boldPriceDivs.flatMap((node) => parsePrices(node.textContent || ''))
                  );
                  const regularBoldPrices = uniqueNumbers(
                    boldPriceDivs
                      .filter((node) => !hasMemberOnlyKeyword(node))
                      .flatMap((node) => parsePrices(node.textContent || ''))
                  );
                  const couponBoldPrices = uniqueNumbers(
                    boldPriceDivs
                      .filter((node) => hasMemberOnlyKeyword(node))
                      .flatMap((node) => parsePrices(node.textContent || ''))
                  );
                  const basePrices = parsePrices(
                    Array.from(customOos.querySelectorAll('del, [class*="basePrice"], [class*="BasePrice"]'))
                      .map((node) => node.textContent || '')
                      .join(' ')
                  );
                  const allCustomPrices = parsePrices(customOos.textContent || '');
                  const originalPrice = basePrices.length
                    ? Math.max(...basePrices)
                    : Math.max(...allCustomPrices, 0);
                  const discountRate = Math.max(...parseDiscountRates(customOos.textContent || ''), 0);

                  if (originalPrice && discountRate) {{
                    const expectedPrices = calculatedDiscountCandidates(originalPrice, discountRate);
                    const matchedRegularPrice = regularBoldPrices.find((price) => expectedPrices.includes(price));
                    if (matchedRegularPrice) {{
                      return String(matchedRegularPrice);
                    }}
                    const matchedAnyPrice = boldPrices.find((price) => expectedPrices.includes(price));
                    if (matchedAnyPrice && !couponBoldPrices.includes(matchedAnyPrice)) {{
                      return String(matchedAnyPrice);
                    }}
                  }}

                  const regularPrice = lowestPrice(boldPriceDivs, {{excludeMemberOnly: true}});
                  if (regularPrice) {{
                    return regularPrice;
                  }}

                  if (couponBoldPrices.length) {{
                    return `\uCFE0\uD3F0 \uD560\uC778\uAC00: ${{Math.min(...couponBoldPrices)}}`;
                  }}
                }}

                const priceElement = element.querySelector(
                  '[class*="Price_priceValue"], strong.price-value, .price-value, [class*="Price_price__"], [class*="PriceArea_priceArea__"], .price, .product-price'
                );
                const directPrice = lowestPrice(priceElement ? [priceElement] : []);
                if (directPrice) {{
                  return directPrice;
                }}

                return lowestPrice(Array.from(element.querySelectorAll('span, strong, div')));
              }};
              const items = [];
              const productList = document.querySelector('#product-list');
              const productRoot = productList || document;
              const rankMarkers = Array.from(productRoot.querySelectorAll('[class*="RankMark_rank"]'))
                .map((marker) => {{
                  const rankClass = Array.from(marker.classList).find((cls) => /^RankMark_rank(\d+)__/.test(cls));
                  const rank = rankClass ? Number(rankClass.replace(/^RankMark_rank(\d+)__.*/, '$1')) : Number.NaN;
                  return {{rank, marker}};
                }})
                .filter((entry) => Number.isFinite(entry.rank) && entry.rank >= 1 && entry.rank <= {max_results})
                .sort((a, b) => a.rank - b.rank)
                .map((entry) => entry.marker);

              const candidates = [];
              const seenElements = new Set();

              for (const rankMarker of rankMarkers) {{
                if (candidates.length >= {max_results}) {{
                  break;
                }}

                const element = rankMarker.closest('li');
                if (!element || seenElements.has(element)) {{
                  continue;
                }}

                seenElements.add(element);
                candidates.push(element);
              }}

              if (!candidates.length) {{
                const productLinks = Array.from(productRoot.querySelectorAll('a[href*="/vp/products/"]'));
                for (const productLink of productLinks) {{
                  if (candidates.length >= {max_results}) {{
                    break;
                  }}
                  const element = productLink.closest('li');
                  if (!element || seenElements.has(element)) {{
                    continue;
                  }}
                  seenElements.add(element);
                  candidates.push(element);
                }}
              }}

              if (!candidates.length) {{
                return {{foundRankMarkers: false, items: []}};
              }}

              for (const element of candidates) {{
                const linkElement = element.querySelector(
                  'a[href*="/vp/products/"]'
                );
                const productLink = linkElement?.href || '';
                const productIdMatch = productLink.match(/\/vp\/products\/(\d+)/);
                const productId = productIdMatch ? productIdMatch[1] : '';
                const titleElement = element.querySelector(
                  '[class*="ProductUnit_productNameV2__"], [class*="ProductUnit_productName__"], div.name, .name, .product-name, .prod-name, a'
                );
                const productName = truncateText(normalizeText(
                  titleElement?.textContent || linkElement?.textContent || ''
                ), 30);
                const price = readPrice(element);
                const ratingElement = element.querySelector(
                  '[class*="rating"], [class*="Rating"], .rating-total > em, .star-rating, .rating-stars'
                );
                const rating = normalizeText(ratingElement?.textContent || '');
                const imageElement = element.querySelector('img');
                const imageUrl = imageElement?.src || imageElement?.dataset?.src || '';

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
              return {{foundRankMarkers: rankMarkers.length > 0, items}};
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

