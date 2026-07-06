from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class ExternalPriceOffer:
    source: str
    title: str
    price: int
    price_text: str
    url: str


def _clean_text(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_price_text(price: int) -> str:
    return f"{price:,}원"


def _extract_price_number(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else None


def _fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urlopen(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="ignore")


def _parse_naver_offers(html: str) -> list[ExternalPriceOffer]:
    offers: list[ExternalPriceOffer] = []
    seen: set[tuple[str, int]] = set()

    for match in re.finditer(
        r'"productName":"(?P<title>[^"]+?)".+?"lowPrice":"(?P<price>\d+)".+?"mallName":"(?P<mall>[^"]+?)".+?"id":"(?P<id>\d+)"',
        html,
    ):
        title = _clean_text(match.group("title"))
        price = int(match.group("price"))
        mall = _clean_text(match.group("mall"))
        if not title or price <= 0:
            continue
        key = (title, price)
        if key in seen:
            continue
        seen.add(key)
        offers.append(
            ExternalPriceOffer(
                source=f"naver:{mall}",
                title=title,
                price=price,
                price_text=_normalize_price_text(price),
                url=f"https://search.shopping.naver.com/product/{match.group('id')}",
            )
        )
        if len(offers) >= 8:
            break

    return offers


def _parse_danawa_offers(html: str) -> list[ExternalPriceOffer]:
    offers: list[ExternalPriceOffer] = []
    seen: set[tuple[str, int]] = set()

    block_pattern = re.compile(
        r'<a[^>]+name="productName"[^>]*>(?P<title>.*?)</a>.*?'
        r'<strong[^>]*class="price_num"[^>]*>(?P<price>.*?)</strong>',
        re.S,
    )
    for match in block_pattern.finditer(html):
        title = _clean_text(match.group("title"))
        price_number = _extract_price_number(match.group("price"))
        if not title or price_number is None:
            continue
        key = (title, price_number)
        if key in seen:
            continue
        seen.add(key)
        offers.append(
            ExternalPriceOffer(
                source="danawa",
                title=title,
                price=price_number,
                price_text=_normalize_price_text(price_number),
                url="https://search.danawa.com/dsearch.php?k1=" + quote(title),
            )
        )
        if len(offers) >= 8:
            break

    return offers


def _score_offer_similarity(reference: str, offer: ExternalPriceOffer) -> float:
    ref_tokens = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", reference.lower()))
    offer_tokens = set(re.findall(r"[0-9A-Za-z가-힣]{2,}", offer.title.lower()))
    if not ref_tokens or not offer_tokens:
        return 0.0
    return len(ref_tokens & offer_tokens) / len(ref_tokens)


def _dedupe_offers(offers: Iterable[ExternalPriceOffer]) -> list[ExternalPriceOffer]:
    deduped: dict[tuple[str, int], ExternalPriceOffer] = {}
    for offer in offers:
        key = (offer.title, offer.price)
        deduped.setdefault(key, offer)
    return list(deduped.values())


async def compare_external_prices(query: str, reference_name: str) -> list[ExternalPriceOffer]:
    encoded = quote(query)
    urls = {
        "naver": f"https://search.shopping.naver.com/search/all?query={encoded}",
        "danawa": f"https://search.danawa.com/dsearch.php?k1={encoded}",
    }

    async def fetch(source: str, url: str) -> list[ExternalPriceOffer]:
        try:
            html = await asyncio.to_thread(_fetch_text, url)
        except Exception:
            return []
        if source == "naver":
            return _parse_naver_offers(html)
        if source == "danawa":
            return _parse_danawa_offers(html)
        return []

    batches = await asyncio.gather(*(fetch(source, url) for source, url in urls.items()))
    offers = _dedupe_offers(offer for batch in batches for offer in batch)
    ranked = sorted(
        offers,
        key=lambda offer: (-_score_offer_similarity(reference_name, offer), offer.price),
    )
    return ranked[:5]


def external_offers_to_dicts(offers: list[ExternalPriceOffer]) -> list[dict[str, str | int]]:
    return [
        {
            "source": offer.source,
            "title": offer.title,
            "price": offer.price,
            "price_text": offer.price_text,
            "url": offer.url,
        }
        for offer in offers
    ]
