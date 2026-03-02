"""OpenAI/Azure Embedding provider 冒烟测试。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.embedding.azure_embedding import AzureEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.openai_embedding import OpenAIEmbedding


ProviderClass = type[OpenAIEmbedding] | type[AzureEmbedding]


def _build_settings(provider: str) -> Settings:
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


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAIEmbedding),
        ("azure", AzureEmbedding),
    ],
)
def test_embedding_factory_create_when_provider_supported_then_route_correctly(
    provider: str,
    provider_class: ProviderClass,
) -> None:
    """配置不同 provider 时，工厂应路由到正确实现。"""

    embedding = EmbeddingFactory.create(_build_settings(provider))

    assert isinstance(embedding, provider_class)


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAIEmbedding),
        ("azure", AzureEmbedding),
    ],
)
def test_embedding_provider_embed_when_mock_response_ok_then_return_vectors(
    provider: str,
    provider_class: ProviderClass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mock 成功响应时应返回批量向量结果。"""

    def _mock_post_embedding(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "data": [
                {"index": 0, "embedding": [0.1, 0.2]},
                {"index": 1, "embedding": [0.3, 0.4]},
            ]
        }

    monkeypatch.setattr(provider_class, "_post_embedding", _mock_post_embedding)
    embedding = provider_class(_build_settings(provider))

    vectors = embedding.embed(["first text", "second text"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAIEmbedding),
        ("azure", AzureEmbedding),
    ],
)
def test_embedding_provider_embed_when_empty_input_then_raise_readable_error(
    provider: str,
    provider_class: ProviderClass,
) -> None:
    """空输入时应抛出可读错误。"""

    embedding = provider_class(_build_settings(provider))

    with pytest.raises(ValueError, match=f"{provider} texts 不能为空"):
        embedding.embed([])


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAIEmbedding),
        ("azure", AzureEmbedding),
    ],
)
def test_embedding_provider_embed_when_text_too_long_and_error_strategy_then_raise(
    provider: str,
    provider_class: ProviderClass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """超长输入且策略为 error 时应抛出可读错误。"""

    monkeypatch.setenv("EMBEDDING_MAX_TEXT_LENGTH", "5")
    monkeypatch.setenv("EMBEDDING_OVERFLOW_STRATEGY", "error")
    embedding = provider_class(_build_settings(provider))

    with pytest.raises(ValueError, match="超长"):
        embedding.embed(["123456"])


@pytest.mark.parametrize(
    ("provider", "provider_class", "error_factory"),
    [
        ("openai", OpenAIEmbedding, TimeoutError),
        ("azure", AzureEmbedding, ConnectionError),
    ],
)
def test_embedding_provider_embed_when_transport_fails_then_raise_runtime_error(
    provider: str,
    provider_class: ProviderClass,
    error_factory: Callable[[str], Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """底层传输异常时应抛出包含 provider 与错误类型的可读错误。"""

    def _mock_post_embedding(self, payload: dict[str, object]) -> dict[str, object]:
        raise error_factory("mock transport failure")

    monkeypatch.setattr(provider_class, "_post_embedding", _mock_post_embedding)
    embedding = provider_class(_build_settings(provider))

    error_type = error_factory.__name__
    with pytest.raises(RuntimeError, match=f"{provider} embed failed: {error_type}"):
        embedding.embed(["hello"])
