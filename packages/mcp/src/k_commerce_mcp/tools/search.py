from k_commerce_cli.services.providers.coupang.search.type import SearchProductResult
from k_commerce_cli.services.tools import invoke_tool
from k_commerce_mcp.tools._result import expect_tool_result


async def search_products(
    provider: str,
    keyword: str,
    category: str | None = None,
    sort: str = "relevance",
    max_results: int = 10,
) -> SearchProductResult:
    return expect_tool_result(
        "search_products",
        await invoke_tool(
            "search_products",
            {
                "provider": provider,
                "keyword": keyword,
                "category": category,
                "sort": sort,
                "max_results": max_results,
            },
        ),
        SearchProductResult,
    )
