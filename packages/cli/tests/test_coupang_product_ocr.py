from k_commerce_cli.services.providers.coupang.product.ocr import _clean_product_ocr_text


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
