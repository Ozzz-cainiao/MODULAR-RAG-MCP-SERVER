"""Unit tests for CompositeEvaluator."""

from __future__ import annotations

from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from libs.evaluator.custom_evaluator import CustomEvaluator
from observability.evaluation.composite_evaluator import CompositeEvaluator
from observability.evaluation.ragas_evaluator import RagasEvaluator


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_composite_evaluator_when_two_evaluators_then_merge_metrics() -> None:
    settings = _build_settings()
    evaluator = CompositeEvaluator(settings, [CustomEvaluator(settings), RagasEvaluator(settings)])

    metrics = evaluator.evaluate("q", ["a"], ["a"])

    assert "hit_rate" in metrics
    assert "faithfulness" in metrics
