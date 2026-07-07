from collections.abc import Callable

import pytest

from k_commerce_cli.services.providers.coupang.product.ocr import _clean_product_ocr_text
from k_commerce_cli.services.providers.coupang.product.ocr import ProductOcrSettings, extract_product_image_text
from k_commerce_cli.services.types import ProductDetailImage


class _FakeChatWatsonx:
    def __init__(
        self,
        model_id: str,
        url: str,
        project_id: str,
        api_key: str,
        max_tokens: int,
        temperature: int,
    ) -> None:
        self.model_id = model_id
        self.url = url
        self.project_id = project_id
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature


def test_clean_product_ocr_text_keeps_final_extracted_text_only() -> None:
    raw = (
        "## Step 1\n"
        "The image is a product detail page.\n\n"
        "## Step 2\n"
        "I will extract the text.\n\n"
        "The final answer is:\n\n"
        "## Product Point\n"
        "- KEY POINT: OFFICE Clamp & SPACE Hook!\n\n"
        "## Specification\n"
        "| 항목 | 설명 |\n"
        "| --- | --- |\n"
        "| 무게 | 70g |\n"
        "| 크기 | 115 x 65 x 25mm |\n"
    )

    cleaned = _clean_product_ocr_text(raw)

    assert "## Step" not in cleaned
    assert "The final answer is" not in cleaned
    assert "Product Point" in cleaned
    assert "| 크기 | 115 x 65 x 25mm |" in cleaned


def test_clean_product_ocr_text_removes_tool_call_artifacts() -> None:
    raw = (
        '<|python_start|>extract_text_from_image(image_url="https://example.com/image.jpg")<|python_end|>\n\n'
        "Product Point\n"
        "OFFICE Clamp & SPACE Hook!\n"
    )

    cleaned = _clean_product_ocr_text(raw)

    assert "python_start" not in cleaned
    assert "extract_text_from_image" not in cleaned
    assert cleaned == "Product Point\nOFFICE Clamp & SPACE Hook!"


@pytest.mark.anyio
async def test_extract_product_image_text_runs_blocking_ocr_in_worker_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_sync_calls: list[str] = []

    def fake_load() -> ProductOcrSettings:
        return ProductOcrSettings(
            url="https://watsonx.example.test",
            project_id="project",
            api_key="key",
            model="model",
        )

    def fake_extract_one_image(model: _FakeChatWatsonx, image_url: str) -> str:
        return f"Final answer:\nOCR for {image_url} with {model.model_id}"

    async def fake_run_sync(
        func: Callable[[_FakeChatWatsonx, str], str],
        model: _FakeChatWatsonx,
        image_url: str,
    ) -> str:
        run_sync_calls.append(image_url)
        return func(model, image_url)

    monkeypatch.setattr("k_commerce_cli.services.providers.coupang.product.ocr.ChatWatsonx", _FakeChatWatsonx)
    monkeypatch.setattr(ProductOcrSettings, "load", staticmethod(fake_load))
    monkeypatch.setattr("k_commerce_cli.services.providers.coupang.product.ocr._extract_one_image", fake_extract_one_image)
    monkeypatch.setattr("k_commerce_cli.services.providers.coupang.product.ocr.anyio.to_thread.run_sync", fake_run_sync)

    images, ocr = await extract_product_image_text((ProductDetailImage(url="https://example.test/detail.jpg"),))

    assert run_sync_calls == ["https://example.test/detail.jpg"]
    assert images == (ProductDetailImage(url="https://example.test/detail.jpg", ocr_status="completed"),)
    assert ocr.status == "completed"
    assert ocr.text == "OCR for https://example.test/detail.jpg with model"
