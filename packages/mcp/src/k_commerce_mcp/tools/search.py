from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.registry import get_provider


async def search_products(
    provider: str,
    keyword: str,
    category: str = "",
    sort: str = "relevance",
    max_results: int = 10,
) -> SearchProductResult:
    return await get_provider(provider).search_products(
        keyword,
        category=category or None,
        sort=sort,
        max_results=max_results,
    )
