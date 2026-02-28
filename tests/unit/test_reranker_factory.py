"""RerankerFactory 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.reranker.base_reranker import BaseReranker, RerankCandidate, TraceContext
from libs.reranker.reranker_factory import NoneReranker, RerankerFactory


class ReverseReranker(BaseReranker):
    """用于测试的自定义 Reranker。"""

    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        trace: TraceContext | None = None,
    ) -> list[RerankCandidate]:
        """返回倒序结果，便于验证路由行为。"""

        return list(reversed(candidates))


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider=provider),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_reranker_factory_create_when_backend_none_then_preserve_original_order() -> None:
    """backend=none 时应保持候选顺序不变。"""

    settings = _build_settings("none")
    reranker = RerankerFactory.create(settings)
    candidates = [
        {"chunk_id": "c1", "score": 0.9},
        {"chunk_id": "c2", "score": 0.8},
    ]

    ranked = reranker.rerank(query="test", candidates=candidates)

    assert isinstance(reranker, NoneReranker)
    assert ranked == candidates


def test_reranker_factory_create_when_custom_provider_registered_then_return_custom_reranker() -> None:
    """已注册 provider 时应返回自定义 Reranker。"""

    provider = "reverse-b5"
    RerankerFactory.register(provider, ReverseReranker)
    settings = _build_settings(provider)
    reranker = RerankerFactory.create(settings)
    candidates = [
        {"chunk_id": "c1", "score": 0.9},
        {"chunk_id": "c2", "score": 0.8},
    ]

    ranked = reranker.rerank(query="test", candidates=candidates)

    assert isinstance(reranker, ReverseReranker)
    assert ranked == list(reversed(candidates))


def test_reranker_factory_create_when_backend_unknown_then_raise_readable_error() -> None:
    """未知 backend 时应抛出可读错误。"""

    settings = _build_settings("unknown-reranker")

    with pytest.raises(ValueError, match="unknown-reranker"):
        RerankerFactory.create(settings)

