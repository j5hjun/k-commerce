import base64
import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult, ImageContent

from k_commerce_cli.services.types import ProductDetailImage, ProductDetailResult
from k_commerce_mcp.server import create_mcp_server
from k_commerce_mcp.tools import _product_images, product

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9sAAAAASUVORK5CYII=")
URL = "https://thumbnail.coupangcdn.com/detail.png"
RESULT = ProductDetailResult(
    success=True, provider="coupang", message="상품 상세", url="https://www.coupang.com/vp/products/1",
    product=None, required_info=(), detail_images=(ProductDetailImage(URL),), sections=(), tables=(),
)


@pytest.fixture
def image_http(monkeypatch):
    requests = []

    def setup(handler):
        def record(request):
            requests.append(request)
            return handler(request)

        client = httpx.AsyncClient(transport=httpx.MockTransport(record))
        monkeypatch.setattr(_product_images.httpx, "AsyncClient", lambda **kwargs: client)
        return requests

    return setup


@pytest.mark.anyio
async def test_registered_tool_returns_original_images_and_product_json_without_env(monkeypatch, tmp_path, image_http):
    monkeypatch.chdir(tmp_path)
    for key in ("WATSONX_URL", "WATSONX_PROJECT_ID", "WATSONX_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    invoke = AsyncMock(return_value=RESULT)
    monkeypatch.setattr(product, "invoke_tool", invoke)
    image_http(lambda request: httpx.Response(200, content=PNG, headers={"content-type": "image/png; charset=binary"}))

    async with create_connected_server_and_client_session(create_mcp_server()) as client:
        result = await client.call_tool("product_detail", {"provider": "coupang", "url": RESULT.url})

    assert isinstance(result, CallToolResult)
    assert result.isError is False
    payload = json.loads(result.content[0].text)
    assert result.structuredContent == payload
    assert payload["detail_images"] == [{"url": URL}]
    assert payload["image_delivery"] == [{"url": URL, "status": "attached"}]
    assert "ocr" not in payload
    assert isinstance(result.content[1], ImageContent)
    assert result.content[1].mimeType == "image/png"
    assert base64.b64decode(result.content[1].data) == PNG
    invoke.assert_awaited_once_with("product_detail", {"provider": "coupang", "url": RESULT.url})


@pytest.mark.anyio
async def test_failed_download_preserves_metadata_and_other_images(monkeypatch, image_http):
    missing = URL + "?missing"
    monkeypatch.setattr(product, "invoke_tool", AsyncMock(return_value=replace(RESULT, detail_images=(ProductDetailImage(missing), ProductDetailImage(URL)))))
    image_http(lambda request: httpx.Response(403) if request.url.query else httpx.Response(200, content=PNG, headers={"content-type": "image/png"}))

    result = await product.product_detail("coupang", RESULT.url)

    assert result.structuredContent["success"] is True
    assert result.isError is False
    assert [item["status"] for item in result.structuredContent["image_delivery"]] == ["failed", "attached"]
    assert len(result.content) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("success", [True, False])
async def test_no_download_on_empty_or_failed_product(monkeypatch, success):
    details = () if success else RESULT.detail_images
    monkeypatch.setattr(product, "invoke_tool", AsyncMock(return_value=replace(RESULT, success=success, detail_images=details)))
    monkeypatch.setattr(_product_images.httpx, "AsyncClient", lambda **kwargs: pytest.fail("unexpected HTTP client"))

    result = await product.product_detail("coupang", RESULT.url)

    assert result.isError is (not success)
    assert len(result.content) == 1
    assert result.structuredContent["image_delivery"] == []


@pytest.mark.anyio
@pytest.mark.parametrize("response,warning", [
    (httpx.Response(200, content=b"<html>blocked</html>", headers={"content-type": "text/html"}), "unsupported_image_type"),
    (httpx.Response(200, headers={"content-type": "image/png"}), "empty_image"),
    (httpx.Response(302, headers={"location": "http://127.0.0.1/private"}), "HTTPStatusError"),
])
async def test_invalid_response_is_not_forwarded_as_image(image_http, response, warning):
    requests = image_http(lambda request: response)
    blocks, delivery = await _product_images.attach_product_images(RESULT.detail_images)
    assert blocks == []
    assert delivery[0]["warning"] == warning
    assert len(requests) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("url", ["http://127.0.0.1/image.png", "https://coupangcdn.com.evil.test/image.png", "file:///etc/passwd"])
async def test_only_public_provider_cdn_urls_are_fetched(image_http, url):
    requests = image_http(lambda request: pytest.fail("unexpected network request"))
    blocks, delivery = await _product_images.attach_product_images((ProductDetailImage(url),))
    assert blocks == []
    assert delivery[0]["warning"] == "unsupported_image_url"
    assert requests == []


@pytest.mark.anyio
@pytest.mark.parametrize("limit,value,expected", [
    ("MAX_IMAGE_BYTES", len(PNG) - 1, ["failed", "failed"]),
    ("MAX_TOTAL_BYTES", len(PNG), ["attached", "skipped"]),
    ("MAX_IMAGES", 1, ["attached", "skipped"]),
    ("DOWNLOAD_DEADLINE_SECONDS", 0, ["skipped", "skipped"]),
])
async def test_attachment_limits_are_reported(monkeypatch, image_http, limit, value, expected):
    monkeypatch.setattr(_product_images, limit, value)
    image_http(lambda request: httpx.Response(200, content=PNG, headers={"content-type": "image/png"}))
    images = (ProductDetailImage(URL), ProductDetailImage(URL + "?second"))

    blocks, delivery = await _product_images.attach_product_images(images)

    assert [item["status"] for item in delivery] == expected
    assert len(blocks) == expected.count("attached")
    assert [item["url"] for item in delivery] == [image.url for image in images]


@pytest.mark.anyio
async def test_timeout_is_reported_without_losing_remaining_images(image_http):
    def handler(request):
        if request.url.query:
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        raise httpx.ReadTimeout("secret transport detail")

    image_http(handler)
    blocks, delivery = await _product_images.attach_product_images((ProductDetailImage(URL), ProductDetailImage(URL + "?second")))
    assert len(blocks) == 1
    assert delivery[0]["warning"] == "ReadTimeout"
    assert delivery[1]["status"] == "attached"
