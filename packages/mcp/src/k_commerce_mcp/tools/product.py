import json

from mcp.types import CallToolResult, TextContent

from k_commerce_cli.services.tools import invoke_tool, to_jsonable
from k_commerce_cli.services.types import ProductDetailResult
from k_commerce_mcp.tools._result import expect_tool_result
from k_commerce_mcp.tools._product_images import attach_product_images


async def product_detail(
    provider: str,
    url: str,
) -> CallToolResult:
    result = expect_tool_result(
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
    payload = to_jsonable(result)
    assert isinstance(payload, dict)
    images, delivery = await attach_product_images(result.detail_images if result.success else ())
    payload["image_delivery"] = delivery
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False)), *images],
        structuredContent=payload,
        isError=not result.success,
    )
