from k_commerce_cli.services.registry import get_provider
from k_commerce_cli.services.types import (
    ListEditableReviewsResult,
    ListReviewsResult,
    ListReviewableResult,
    ReviewDeleteRequest,
    ReviewDeleteResult,
    ReviewEditRequest,
    ReviewEditResult,
    ReviewUploadRequest,
    ReviewUploadResult,
)


async def review_list_reviewable(provider: str) -> ListReviewableResult:
    return await get_provider(provider).list_reviewable()


async def review_list_editable(provider: str) -> ListEditableReviewsResult:
    return await get_provider(provider).list_editable()


async def review_list(provider: str) -> ListReviewsResult:
    return await get_provider(provider).list_reviews()


async def review_upload(
    provider: str,
    order_id: str,
    product_id: str,
    rating: int,
    text: str,
    review_url: str,
) -> ReviewUploadResult:
    return await get_provider(provider).upload_review(
        ReviewUploadRequest(
            order_id=order_id,
            product_id=product_id,
            rating=rating,
            text=text,
            review_url=review_url,
        )
    )


async def review_edit(
    provider: str,
    order_id: str,
    product_id: str,
    review_id: str,
    rating: int,
    text: str,
) -> ReviewEditResult:
    return await get_provider(provider).edit_review(
        ReviewEditRequest(
            order_id=order_id,
            product_id=product_id,
            review_id=review_id,
            rating=rating,
            text=text,
        )
    )


async def review_delete(
    provider: str,
    review_id: str,
    product_id: str = "",
    order_id: str = "",
) -> ReviewDeleteResult:
    return await get_provider(provider).delete_review(
        ReviewDeleteRequest(
            review_id=review_id,
            product_id=product_id,
            order_id=order_id,
        )
    )
