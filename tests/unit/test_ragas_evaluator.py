"""Unit tests for RagasEvaluator."""

from __future__ import annotations

from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from observability.evaluation.ragas_evaluator import RagasEvaluator


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="ragas"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_ragas_evaluator_when_overlap_exists_then_return_metrics() -> None:
    evaluator = RagasEvaluator(_build_settings())

    metrics = evaluator.evaluate("q", ["a", "b"], ["b"])

    assert set(metrics.keys()) == {"faithfulness", "answer_relevancy", "context_precision"}
    assert metrics["faithfulness"] == 1.0
