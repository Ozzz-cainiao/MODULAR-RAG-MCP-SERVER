"""Ollama Embedding 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.ollama_embedding import OllamaEmbedding


def _build_settings(provider: str = "ollama") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider=provider),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_embedding_factory_create_when_provider_ollama_then_return_ollama_embedding() -> None:
    """provider=ollama 时工厂应返回 OllamaEmbedding。"""

    embedding = EmbeddingFactory.create(_build_settings("ollama"))

    assert isinstance(embedding, OllamaEmbedding)


def test_ollama_embedding_embed_when_mock_batch_response_then_return_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mock 批量响应时应返回批量向量结果。"""

    def _mock_post_embed(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "embeddings": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ]
        }

    monkeypatch.setattr(OllamaEmbedding, "_post_embed", _mock_post_embed)
    embedding = OllamaEmbedding(_build_settings())

    vectors = embedding.embed(["first text", "second text"])

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert len(vectors[0]) == 3


def test_ollama_embedding_embed_when_mock_single_response_then_return_single_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mock 单条响应时应返回单向量列表。"""

    def _mock_post_embed(self, payload: dict[str, object]) -> dict[str, object]:
        return {"embedding": [0.9, 1.1]}

    monkeypatch.setattr(OllamaEmbedding, "_post_embed", _mock_post_embed)
    embedding = OllamaEmbedding(_build_settings())

    vectors = embedding.embed(["single text"])

    assert vectors == [[0.9, 1.1]]


def test_ollama_embedding_embed_when_empty_input_then_raise_readable_error() -> None:
    """空输入时应抛出可读错误。"""

    embedding = OllamaEmbedding(_build_settings())

    with pytest.raises(ValueError, match="ollama texts 不能为空"):
        embedding.embed([])


def test_ollama_embedding_embed_when_text_too_long_then_raise_or_truncate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """超长输入时应按策略报错或截断。"""

    monkeypatch.setenv("EMBEDDING_MAX_TEXT_LENGTH", "5")
    monkeypatch.setenv("EMBEDDING_OVERFLOW_STRATEGY", "error")
    embedding = OllamaEmbedding(_build_settings())

    with pytest.raises(ValueError, match="超长"):
        embedding.embed(["123456"])


@pytest.mark.parametrize("error_type", [ConnectionError, TimeoutError])
def test_ollama_embedding_embed_when_transport_fails_then_raise_runtime_error(
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """连接失败或超时时应抛出可读错误。"""

    def _mock_post_embed(self, payload: dict[str, object]) -> dict[str, object]:
        raise error_type("mock transport failure")

    monkeypatch.setattr(OllamaEmbedding, "_post_embed", _mock_post_embed)
    embedding = OllamaEmbedding(_build_settings())

    with pytest.raises(RuntimeError, match=f"ollama embed failed: {error_type.__name__}") as exc_info:
        embedding.embed(["hello"])

    message = str(exc_info.value)
    assert "api_key" not in message
    assert "OLLAMA_API_KEY" not in message

