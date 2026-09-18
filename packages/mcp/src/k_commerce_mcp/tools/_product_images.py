"""Adapt scraped image URLs to MCP image blocks without invoking a model."""

from base64 import b64encode

import anyio
import httpx
from mcp.types import ImageContent

from k_commerce_cli.services.types import ProductDetailImage

MAX_IMAGES = 20
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
DOWNLOAD_DEADLINE_SECONDS = 30
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def _download_image(client: httpx.AsyncClient, url: str, byte_limit: int) -> tuple[bytes, str]:
    parsed = httpx.URL(url)
    # URLs originate in page content. Only fetch this provider's public image CDN;
    # do not follow redirects to arbitrary hosts or forward browser credentials.
    if parsed.scheme != "https" or not (parsed.host == "coupangcdn.com" or parsed.host.endswith(".coupangcdn.com")) or parsed.port not in (None, 443) or parsed.userinfo:
        raise ValueError("unsupported_image_url")
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime_type not in IMAGE_MIME_TYPES:
            raise ValueError("unsupported_image_type")
        data = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
            if len(data) + len(chunk) > byte_limit:
                raise ValueError("image_size_limit")
            data.extend(chunk)
        if not data:
            raise ValueError("empty_image")
        return bytes(data), mime_type


async def attach_product_images(images: tuple[ProductDetailImage, ...]) -> tuple[list[ImageContent], list[dict[str, str]]]:
    """Keep source order and report every attachment, failure, and skipped image."""
    blocks: list[ImageContent] = []
    delivery: list[dict[str, str]] = []
    if not images:
        return blocks, delivery

    total_bytes = 0
    deadline = anyio.current_time() + DOWNLOAD_DEADLINE_SECONDS
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        for index, image in enumerate(images):
            item = {"url": image.url, "status": "skipped"}
            delivery.append(item)
            remaining = deadline - anyio.current_time()
            if index >= MAX_IMAGES or total_bytes >= MAX_TOTAL_BYTES:
                item["warning"] = "attachment_limit"
                continue
            if remaining <= 0:
                item["warning"] = "download_deadline"
                continue
            try:
                with anyio.fail_after(remaining):
                    data, mime_type = await _download_image(client, image.url, min(MAX_IMAGE_BYTES, MAX_TOTAL_BYTES - total_bytes))
            except (httpx.HTTPError, httpx.InvalidURL, ValueError, TimeoutError) as exc:
                item["status"] = "failed"
                item["warning"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                continue
            total_bytes += len(data)
            blocks.append(ImageContent(type="image", data=b64encode(data).decode("ascii"), mimeType=mime_type))
            item["status"] = "attached"
    return blocks, delivery
