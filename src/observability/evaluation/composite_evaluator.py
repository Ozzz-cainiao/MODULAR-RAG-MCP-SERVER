"""Composite evaluator wrapper."""

from __future__ import annotations

from libs.evaluator.base_evaluator import BaseEvaluator, EvaluationMetrics, TraceContext


class CompositeEvaluator(BaseEvaluator):
    """Run multiple evaluators and merge their metrics."""

    def __init__(self, settings, evaluators: list[BaseEvaluator]) -> None:
        super().__init__(settings)
        self._evaluators = evaluators

    def evaluate(
        self,
        query: str,
        retrieved_ids: list[str],
        golden_ids: list[str],
        trace: TraceContext | None = None,
    ) -> EvaluationMetrics:
        metrics: EvaluationMetrics = {}
        for evaluator in self._evaluators:
            metrics.update(evaluator.evaluate(query, retrieved_ids, golden_ids, trace=trace))
        return metrics
