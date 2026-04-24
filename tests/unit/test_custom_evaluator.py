"""CustomEvaluator 与 EvaluatorFactory 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.evaluator.custom_evaluator import CustomEvaluator
from libs.evaluator.evaluator_factory import EvaluatorFactory
from observability.evaluation.composite_evaluator import CompositeEvaluator


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider=provider),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_custom_evaluator_evaluate_when_hit_then_return_hit_rate_and_mrr() -> None:
    """命中 golden_ids 时应返回稳定指标。"""

    settings = _build_settings("custom")
    evaluator = CustomEvaluator(settings)

    metrics = evaluator.evaluate(
        query="如何进行模块拆分",
        retrieved_ids=["doc-1", "doc-2", "doc-3"],
        golden_ids=["doc-2", "doc-9"],
    )

    assert metrics["hit_rate"] == 1.0
    assert metrics["mrr"] == 0.5


def test_custom_evaluator_evaluate_when_miss_then_return_zero_metrics() -> None:
    """未命中 golden_ids 时应返回 0 指标。"""

    settings = _build_settings("custom")
    evaluator = CustomEvaluator(settings)

    metrics = evaluator.evaluate(
        query="什么是契约测试",
        retrieved_ids=["doc-a", "doc-b"],
        golden_ids=["doc-z"],
    )

    assert metrics == {"hit_rate": 0.0, "mrr": 0.0}


def test_evaluator_factory_create_when_provider_custom_then_return_custom_evaluator() -> None:
    """provider=custom 时工厂应返回 CustomEvaluator。"""

    settings = _build_settings("custom")

    evaluator = EvaluatorFactory.create(settings)

    assert isinstance(evaluator, CustomEvaluator)


def test_evaluator_factory_create_when_provider_missing_then_raise_readable_error() -> None:
    """未知 provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-evaluator")

    with pytest.raises(ValueError, match="not-registered-evaluator"):
        EvaluatorFactory.create(settings)


def test_custom_evaluator_evaluate_when_golden_ids_empty_then_return_zero_metrics() -> None:
    settings = _build_settings("custom")
    evaluator = CustomEvaluator(settings)

    metrics = evaluator.evaluate(query="q", retrieved_ids=["a"], golden_ids=[])

    assert metrics == {"hit_rate": 0.0, "mrr": 0.0}


def test_evaluator_factory_create_composite_when_two_backends_then_return_composite() -> None:
    settings = _build_settings("custom")

    evaluator = EvaluatorFactory.create_composite(settings, ["custom", "ragas"])

    assert isinstance(evaluator, CompositeEvaluator)
