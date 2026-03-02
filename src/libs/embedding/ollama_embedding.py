"""Ollama Embedding 适配器实现。"""

from __future__ import annotations

import os
from collections.abc import Mapping

from core.settings import Settings
from libs.embedding.base_embedding import BaseEmbedding, TraceContext
from libs.embedding.openai_embedding import _post_json, _validate_texts


class OllamaEmbedding(BaseEmbedding):
    """Ollama 本地 Embedding 适配器。"""

    provider_name = "ollama"

    def __init__(self, settings: Settings) -> None:
        """初始化 Ollama Embedding。"""

        super().__init__(settings)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv(
            "OLLAMA_EMBEDDING_MODEL",
            os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
        )

    def embed(
        self,
        texts: list[str],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """调用 Ollama Embedding 接口并返回向量列表。"""

        normalized_texts = _validate_texts(texts, self.provider_name)
        payload = {
            "model": self.model,
            "input": normalized_texts,
        }

        try:
            response = self._post_embed(payload)
            return _extract_ollama_embeddings(
                response=response,
                provider=self.provider_name,
                expected_count=len(normalized_texts),
            )
        except ValueError:
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise RuntimeError(f"{self.provider_name} embed failed: {error_type}: {error}") from error

    def _post_embed(self, payload: dict[str, object]) -> Mapping[str, object]:
        """发送 HTTP 请求到 Ollama Embedding 接口。"""

        url = f"{self.base_url}/api/embed"
        return _post_json(url=url, headers={}, payload=payload)


def _extract_ollama_embeddings(
    response: Mapping[str, object],
    provider: str,
    expected_count: int,
) -> list[list[float]]:
    """从 Ollama 响应中提取向量列表。"""

    if not isinstance(response, Mapping):
        raise ValueError(f"{provider} 响应格式非法")

    vectors: list[list[float]] = []

    embeddings = response.get("embeddings")
    if isinstance(embeddings, list):
        for index, item in enumerate(embeddings):
            if not isinstance(item, list) or not all(isinstance(value, (int, float)) for value in item):
                raise ValueError(f"{provider} 响应 embeddings[{index}] 格式非法")
            vectors.append([float(value) for value in item])
    else:
        single_embedding = response.get("embedding")
        if isinstance(single_embedding, list) and all(isinstance(value, (int, float)) for value in single_embedding):
            vectors.append([float(value) for value in single_embedding])

    if not vectors:
        raise ValueError(f"{provider} 响应缺少 embedding 向量")
    if len(vectors) != expected_count:
        raise ValueError(f"{provider} 响应向量数量不匹配，期望 {expected_count}，实际 {len(vectors)}")

    return vectors

