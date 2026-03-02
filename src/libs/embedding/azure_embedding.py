"""Azure OpenAI Embedding 适配器实现。"""

from __future__ import annotations

import os
from collections.abc import Mapping

from core.settings import Settings
from libs.embedding.base_embedding import BaseEmbedding, TraceContext
from libs.embedding.openai_embedding import _extract_embeddings, _post_json, _validate_texts


class AzureEmbedding(BaseEmbedding):
    """Azure OpenAI Embedding 适配器。"""

    provider_name = "azure"

    def __init__(self, settings: Settings) -> None:
        """初始化 Azure OpenAI Embedding。"""

        super().__init__(settings)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://example-resource.openai.azure.com")
        self.deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

    def embed(
        self,
        texts: list[str],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """调用 Azure OpenAI Embedding 接口并返回向量列表。"""

        normalized_texts = _validate_texts(texts, self.provider_name)
        payload = {
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
        """发送 HTTP 请求到 Azure OpenAI Embedding 接口。"""

        normalized_endpoint = self.endpoint.rstrip("/")
        url = (
            f"{normalized_endpoint}/openai/deployments/{self.deployment}"
            f"/embeddings?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key}
        return _post_json(url=url, headers=headers, payload=payload)

