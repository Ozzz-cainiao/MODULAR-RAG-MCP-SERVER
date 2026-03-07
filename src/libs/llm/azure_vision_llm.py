"""Azure Vision LLM 适配器实现。"""

from __future__ import annotations

import base64
import binascii
import io
import os
from pathlib import Path
from typing import Any

from core.settings import Settings
from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse, TraceContext
from libs.llm.openai_llm import _extract_content, _post_json


class AzureVisionLLM(BaseVisionLLM):
    """Azure OpenAI Vision LLM 适配器。"""

    provider_name = "azure"

    def __init__(self, settings: Settings) -> None:
        """初始化 Azure Vision LLM。"""

        super().__init__(settings)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://example-resource.openai.azure.com")
        self.deployment = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "gpt-4o")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.max_image_size = int(os.getenv("VISION_MAX_IMAGE_SIZE", "2048"))

    def chat_with_image(
        self,
        text: str,
        image_input: str | bytes,
        trace: TraceContext | None = None,
    ) -> ChatResponse:
        """执行多模态对话并返回结构化结果。"""

        if not isinstance(text, str) or not text.strip():
            raise ValueError("text 必须是非空字符串")

        try:
            image_bytes, mime_type = _load_image_bytes(image_input)
            image_bytes = _resize_image_bytes(image_bytes, self.max_image_size)
            image_url = _build_data_url(image_bytes, mime_type)

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": text.strip()},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ]
            }

            response = self._post_chat(payload)
            _raise_if_azure_error(response)
            return {"text": _extract_content(response, self.provider_name)}
        except ValueError:
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise RuntimeError(f"{self.provider_name} vision chat failed: {error_type}: {error}") from error

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """发送 HTTP 请求到 Azure Vision Chat 接口。"""

        normalized_endpoint = self.endpoint.rstrip("/")
        url = (
            f"{normalized_endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key}
        return dict(_post_json(url=url, headers=headers, payload=payload))


def _load_image_bytes(image_input: str | bytes) -> tuple[bytes, str]:
    """从路径或 base64 获取图片 bytes，并返回 mime 类型。"""

    if isinstance(image_input, bytes):
        return image_input, "image/png"

    if not isinstance(image_input, str) or not image_input.strip():
        raise ValueError("image_input 必须是图片路径或 base64 字符串")

    candidate = image_input.strip()
    path = Path(candidate)
    if path.exists():
        image_bytes = path.read_bytes()
        return image_bytes, _infer_mime_type(path.suffix)

    try:
        image_bytes = base64.b64decode(candidate, validate=True)
    except (ValueError, binascii.Error) as error:  # type: ignore[name-defined]
        raise ValueError("image_input 不是有效的 base64 字符串") from error

    return image_bytes, "image/png"


def _infer_mime_type(suffix: str) -> str:
    """根据文件扩展名推断 mime 类型。"""

    suffix_lower = suffix.lower()
    if suffix_lower in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix_lower == ".webp":
        return "image/webp"
    if suffix_lower == ".png":
        return "image/png"
    return "image/png"


def _build_data_url(image_bytes: bytes, mime_type: str) -> str:
    """构造 data URL。"""

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _resize_image_bytes(image_bytes: bytes, max_size: int) -> bytes:
    """按 max_size 进行图片压缩（无依赖时返回原图）。"""

    if max_size <= 0:
        return image_bytes

    try:
        from PIL import Image
    except Exception:
        return image_bytes

    with Image.open(io.BytesIO(image_bytes)) as image:
        if max(image.size) <= max_size:
            return image_bytes

        image.thumbnail((max_size, max_size))
        output = io.BytesIO()
        image.save(output, format=image.format or "PNG")
        return output.getvalue()


def _raise_if_azure_error(response: dict[str, Any]) -> None:
    """当 Azure 返回错误结构时抛出可读错误。"""

    error_info = response.get("error")
    if not isinstance(error_info, dict):
        return

    code = error_info.get("code", "unknown_error")
    message = error_info.get("message", "Azure Vision LLM error")
    raise ValueError(f"Azure Vision LLM error: {code}: {message}")
