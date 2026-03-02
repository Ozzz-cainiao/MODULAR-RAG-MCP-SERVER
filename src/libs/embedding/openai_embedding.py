"""OpenAI Embedding 适配器实现。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from urllib.request import Request, urlopen

from core.settings import Settings
from libs.embedding.base_embedding import BaseEmbedding, TraceContext


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding 适配器。"""

    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        """初始化 OpenAI Embedding。"""

        super().__init__(settings)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def embed(
        self,
        texts: list[str],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """调用 OpenAI Embedding 接口并返回向量列表。"""

        normalized_texts = _validate_texts(texts, self.provider_name)
        payload = {
            "model": self.model,
            "input": normalized_texts,
        }

        try:
            response = self._post_embedding(payload)
            return _extract_embeddings(response, self.provider_name)
        except ValueError:
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise RuntimeError(f"{self.provider_name} embed failed: {error_type}: {error}") from error

    def _post_embedding(self, payload: dict[str, object]) -> Mapping[str, object]:
        """发送 HTTP 请求到 OpenAI Embedding 接口。"""

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/embeddings"
        return _post_json(url=url, headers=headers, payload=payload)


def _validate_texts(texts: list[str], provider: str) -> list[str]:
    """校验并规范化输入文本列表。"""

    if not isinstance(texts, list):
        raise ValueError(f"{provider} texts 必须是 list[str]")
    if not texts:
        raise ValueError(f"{provider} texts 不能为空")

    max_length = int(os.getenv("EMBEDDING_MAX_TEXT_LENGTH", "8192"))
    overflow_strategy = os.getenv("EMBEDDING_OVERFLOW_STRATEGY", "error").strip().lower()

    normalized_texts: list[str] = []
    for index, text in enumerate(texts):
        if not isinstance(text, str):
            raise ValueError(f"{provider} texts[{index}] 必须是字符串")

        normalized = text.strip()
        if not normalized:
            raise ValueError(f"{provider} texts[{index}] 不能为空字符串")

        if len(normalized) > max_length:
            if overflow_strategy == "truncate":
                normalized = normalized[:max_length]
            else:
                raise ValueError(f"{provider} texts[{index}] 超长，长度上限为 {max_length}")

        normalized_texts.append(normalized)

    return normalized_texts


def _extract_embeddings(response: Mapping[str, object], provider: str) -> list[list[float]]:
    """从响应体提取 embedding 向量列表。"""

    data = response.get("data") if isinstance(response, Mapping) else None
    if not isinstance(data, list) or not data:
        raise ValueError(f"{provider} 响应缺少 data")

    ordered_items: list[tuple[int, list[float]]] = []
    for index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise ValueError(f"{provider} 响应 data[{index}] 格式非法")

        raw_index = item.get("index", index)
        if not isinstance(raw_index, int):
            raise ValueError(f"{provider} 响应 data[{index}].index 格式非法")

        embedding = item.get("embedding")
        if not isinstance(embedding, list) or not all(isinstance(value, (int, float)) for value in embedding):
            raise ValueError(f"{provider} 响应 data[{index}].embedding 格式非法")

        ordered_items.append((raw_index, [float(value) for value in embedding]))

    ordered_items.sort(key=lambda pair: pair[0])
    return [item[1] for item in ordered_items]


def _post_json(url: str, headers: dict[str, str], payload: dict[str, object]) -> Mapping[str, object]:
    """发送 JSON POST 请求并解析响应。"""

    request_headers = {"Content-Type": "application/json", **headers}
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        response_text = response.read().decode("utf-8")

    parsed = json.loads(response_text)
    if not isinstance(parsed, Mapping):
        raise ValueError("响应体必须是 JSON 对象")

    return parsed

