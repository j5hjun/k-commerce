from __future__ import annotations

import os
import re
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx
from ibm_watsonx_ai.wml_client_error import WMLClientError
from langchain_core.messages import HumanMessage
from langchain_ibm import ChatWatsonx

from k_commerce_cli.services.types import ProductDetailImage, ProductOcrResult

DEFAULT_PRODUCT_OCR_MODEL: Final = "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"
PRODUCT_OCR_SCOPE: Final = "full"
FINAL_ANSWER_MARKERS: Final = (
    "The final answer is:",
    "Final answer:",
    "최종 답변은:",
    "최종 답변:",
    "최종 결과:",
)
TOOL_ARTIFACT_PATTERN: Final = re.compile(r"<\|[^|]+?\|>|extract_text_from_image\([^)]*\)")


@dataclass(frozen=True, slots=True)
class ProductOcrSettings:
    url: str
    project_id: str
    api_key: str
    model: str = DEFAULT_PRODUCT_OCR_MODEL

    @classmethod
    def load(cls) -> "ProductOcrSettings | None":
        values = _read_dotenv(Path.cwd() / ".env") | dict(os.environ)
        url = values.get("WATSONX_URL", "")
        project_id = values.get("WATSONX_PROJECT_ID", "")
        api_key = values.get("WATSONX_API_KEY", "")
        model = values.get("PRODUCT_OCR_MODEL") or values.get("AGENT_PRODUCT_OCR_MODEL") or DEFAULT_PRODUCT_OCR_MODEL
        if not url or not project_id or not api_key:
            return None
        return cls(url=url, project_id=project_id, api_key=api_key, model=model)


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw_value = stripped.split("=", 1)
        values[name.strip()] = raw_value.strip().strip('"').strip("'")
    return values


async def extract_product_image_text(
    images: tuple[ProductDetailImage, ...],
) -> tuple[tuple[ProductDetailImage, ...], ProductOcrResult]:
    if not images:
        return images, ProductOcrResult(enabled=True, status="no_images", model="", scope=PRODUCT_OCR_SCOPE)

    settings = ProductOcrSettings.load()
    if settings is None:
        return images, ProductOcrResult(
            enabled=True,
            status="model_unavailable",
            model="",
            scope=PRODUCT_OCR_SCOPE,
            warnings=("WATSONX_URL, WATSONX_PROJECT_ID, WATSONX_API_KEY 설정이 필요합니다.",),
        )

    model = ChatWatsonx(
        model_id=settings.model,
        url=settings.url,
        project_id=settings.project_id,
        api_key=settings.api_key,
        max_tokens=700,
        temperature=0,
    )
    updated_images: list[ProductDetailImage] = []
    texts: list[str] = []
    warnings: list[str] = []

    for image in images:
        try:
            content = _extract_one_image(model, image.url)
        except (WMLClientError, httpx.HTTPError, RuntimeError, ValueError, OSError, TimeoutError) as exc:
            warning = f"OCR 실패: {type(exc).__name__}"
            warnings.append(warning)
            updated_images.append(ProductDetailImage(url=image.url, ocr_status="failed", warning=warning))
            continue
        text = _clean_product_ocr_text(content)
        texts.append(text)
        updated_images.append(ProductDetailImage(url=image.url, ocr_status="completed"))

    status = "completed" if not warnings else "partial"
    if not texts:
        status = "failed"
    return tuple(updated_images), ProductOcrResult(
        enabled=True,
        status=status,
        model=settings.model,
        scope=PRODUCT_OCR_SCOPE,
        text="\n\n".join(texts),
        confidence="medium" if texts else "",
        warnings=tuple(warnings),
    )


def _extract_one_image(model: ChatWatsonx, image_url: str) -> str:
    content_url = _image_content_url(image_url)
    response = model.invoke(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": _product_ocr_prompt()},
                    {"type": "image_url", "image_url": {"url": content_url}},
                ]
            )
        ]
    )
    content = response.content
    if isinstance(content, str):
        return content
    return str(content)


def _clean_product_ocr_text(raw_text: str) -> str:
    text = _remove_tool_artifacts(raw_text)
    text = _text_after_final_answer_marker(text)
    return _normalize_ocr_text(text)


def _remove_tool_artifacts(raw_text: str) -> str:
    lines: list[str] = []
    for line in raw_text.splitlines():
        cleaned = TOOL_ARTIFACT_PATTERN.sub("", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _text_after_final_answer_marker(raw_text: str) -> str:
    selected_index = -1
    selected_marker = ""
    lowered = raw_text.lower()
    for marker in FINAL_ANSWER_MARKERS:
        index = lowered.rfind(marker.lower())
        if index > selected_index:
            selected_index = index
            selected_marker = marker
    if selected_index < 0:
        return raw_text
    return raw_text[selected_index + len(selected_marker) :]


def _normalize_ocr_text(raw_text: str) -> str:
    lines: list[str] = []
    previous_blank = False
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines and not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(stripped)
        previous_blank = False
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _image_content_url(image_url: str) -> str:
    if image_url.startswith("data:image/"):
        return image_url
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(image_url)
        response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg").split(";", 1)[0]
    encoded = b64encode(response.content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _product_ocr_prompt() -> str:
    return (
        "이미지에 실제로 보이는 상품 상세 설명 본문 텍스트만 OCR 결과처럼 그대로 추출해줘.\n"
        "분석 과정, 단계 설명, 요약, 번역, 추측, 사과, OCR 방법 안내, 코드 호출 문구는 절대 쓰지 마.\n"
        "이미지에 없는 내용은 만들지 마.\n"
        "표가 보이면 행과 열을 Markdown 표로 보존해.\n"
        "텍스트가 거의 없으면 `텍스트 없음`만 출력해."
    )
