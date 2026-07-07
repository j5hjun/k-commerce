from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import ProductDetailResult
from k_commerce_mcp.tools._result import expect_tool_result


async def product_detail(
    provider: str,
    url: str,
) -> ProductDetailResult:
    return expect_tool_result(
        "product_detail",
        await invoke_tool(
            "product_detail",
            {
                "provider": provider,
                "url": url,
            },
        ),
        ProductDetailResult,
    )
