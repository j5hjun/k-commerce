from k_commerce_cli.services.tools import invoke_tool
from k_commerce_cli.services.types import (
    ListEditableReviewsResult,
    ListReviewableResult,
    ReviewDeleteResult,
    ReviewEditResult,
    ReviewUploadResult,
)
from k_commerce_mcp.tools._result import expect_tool_result


async def review_list_reviewable(provider: str) -> ListReviewableResult:
    return expect_tool_result("review_list_reviewable", await invoke_tool("review_list_reviewable", {"provider": provider}), ListReviewableResult)


async def review_list_editable(provider: str) -> ListEditableReviewsResult:
    return expect_tool_result("review_list_editable", await invoke_tool("review_list_editable", {"provider": provider}), ListEditableReviewsResult)


async def review_upload(
    provider: str,
    order_id: str,
    product_id: str,
    rating: int,
    text: str,
    review_url: str,
) -> ReviewUploadResult:
    return expect_tool_result(
        "review_upload",
        await invoke_tool(
            "review_upload",
            {
                "provider": provider,
                "order_id": order_id,
                "product_id": product_id,
                "rating": rating,
                "text": text,
                "review_url": review_url,
            },
        ),
        ReviewUploadResult,
    )


async def review_edit(
    provider: str,
    order_id: str,
    product_id: str,
    review_id: str,
    rating: int,
    text: str,
) -> ReviewEditResult:
    return expect_tool_result(
        "review_edit",
        await invoke_tool(
            "review_edit",
            {
                "provider": provider,
                "order_id": order_id,
                "product_id": product_id,
                "review_id": review_id,
                "rating": rating,
                "text": text,
            },
        ),
        ReviewEditResult,
    )


async def review_delete(
    provider: str,
    review_id: str,
    product_id: str = "",
    order_id: str = "",
) -> ReviewDeleteResult:
    return expect_tool_result(
        "review_delete",
        await invoke_tool(
            "review_delete",
            {
                "provider": provider,
                "review_id": review_id,
                "product_id": product_id,
                "order_id": order_id,
            },
        ),
        ReviewDeleteResult,
    )
