"""EmbeddingFactory 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.embedding.base_embedding import BaseEmbedding, TraceContext
from libs.embedding.embedding_factory import EmbeddingFactory


class FakeEmbedding(BaseEmbedding):
    """用于测试的 Fake Embedding 实现。"""

    def embed(
        self,
        texts: list[str],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """返回稳定向量，便于断言工厂路由结果。"""

        return [[float(index), float(len(text))] for index, text in enumerate(texts)]


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider=provider),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_embedding_factory_create_when_provider_registered_then_return_fake_embedding() -> None:
    """已注册 provider 时应返回对应实现。"""

    provider = "fake-embedding-b2"
    EmbeddingFactory.register(provider, FakeEmbedding)
    settings = _build_settings(provider)

    embedding = EmbeddingFactory.create(settings)

    assert isinstance(embedding, FakeEmbedding)
    assert embedding.embed(["a", "abcd"]) == [[0.0, 1.0], [1.0, 4.0]]


def test_embedding_factory_create_when_provider_missing_then_raise_readable_error() -> None:
    """未注册 provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-embedding")

    with pytest.raises(ValueError, match="not-registered-embedding"):
        EmbeddingFactory.create(settings)

