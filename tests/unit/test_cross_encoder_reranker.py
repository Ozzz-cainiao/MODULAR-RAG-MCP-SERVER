"""CrossEncoderReranker 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.reranker.cross_encoder_reranker import CrossEncoderReranker
from libs.reranker.reranker_factory import RerankerFactory


def _build_settings(rerank_provider: str = "cross_encoder") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider=rerank_provider),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_reranker_factory_create_when_provider_cross_encoder_then_return_cross_encoder_reranker() -> None:
    """backend=cross_encoder 时工厂应返回 CrossEncoderReranker。"""

    reranker = RerankerFactory.create(_build_settings("cross_encoder"))

    assert isinstance(reranker, CrossEncoderReranker)


def test_cross_encoder_reranker_rerank_when_scores_mocked_then_top_m_sorted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """对 Top-M 候选应按打分排序，尾部候选保持原顺序。"""

    monkeypatch.setenv("RERANK_TOP_M", "2")
    reranker = CrossEncoderReranker(_build_settings())

    def _mock_score_candidates(self, query: str, candidates):
        assert len(candidates) == 2
        return [0.1, 0.9]

    monkeypatch.setattr(CrossEncoderReranker, "_score_candidates", _mock_score_candidates)

    candidates = [
        {"chunk_id": "c1", "text": "alpha", "metadata": {}},
        {"chunk_id": "c2", "text": "beta", "metadata": {}},
        {"chunk_id": "c3", "text": "gamma", "metadata": {}},
    ]

    ranked = reranker.rerank(query="query", candidates=candidates)

    assert [item["chunk_id"] for item in ranked] == ["c2", "c1", "c3"]


@pytest.mark.parametrize("error_type", [TimeoutError, RuntimeError])
def test_cross_encoder_reranker_rerank_when_scorer_failed_then_return_fallback_signal(
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打分失败时应返回回退信号并保持原顺序。"""

    reranker = CrossEncoderReranker(_build_settings())

    def _mock_score_candidates(self, query: str, candidates):
        raise error_type("mock scorer failed")

    monkeypatch.setattr(CrossEncoderReranker, "_score_candidates", _mock_score_candidates)

    candidates = [
        {"chunk_id": "c1", "text": "first", "metadata": {"source": "a"}},
        {"chunk_id": "c2", "text": "second", "metadata": {"source": "b"}},
    ]

    ranked = reranker.rerank(query="query", candidates=candidates)

    assert [item["chunk_id"] for item in ranked] == ["c1", "c2"]
    assert ranked[0]["metadata"]["rerank_fallback"] == "cross_encoder_failed"
    assert ranked[1]["metadata"]["rerank_fallback"] == "cross_encoder_failed"


def test_cross_encoder_reranker_rerank_when_score_count_mismatch_then_raise_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """打分数量与候选数量不一致时应抛出可读错误。"""

    reranker = CrossEncoderReranker(_build_settings())

    def _mock_score_candidates(self, query: str, candidates):
        return [0.5]

    monkeypatch.setattr(CrossEncoderReranker, "_score_candidates", _mock_score_candidates)

    with pytest.raises(ValueError, match="打分数量"):
        reranker.rerank(
            query="query",
            candidates=[
                {"chunk_id": "c1", "text": "first", "metadata": {}},
                {"chunk_id": "c2", "text": "second", "metadata": {}},
            ],
        )

