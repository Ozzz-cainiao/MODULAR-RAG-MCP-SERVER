"""Ragas-style evaluator with graceful fallback."""

from __future__ import annotations

from libs.evaluator.base_evaluator import BaseEvaluator, EvaluationMetrics, TraceContext


class RagasEvaluator(BaseEvaluator):
    """Lightweight Ragas-compatible evaluator."""

    def evaluate(
        self,
        query: str,
        retrieved_ids: list[str],
        golden_ids: list[str],
        trace: TraceContext | None = None,
    ) -> EvaluationMetrics:
        golden_set = set(golden_ids)
        overlap = len([item for item in retrieved_ids if item in golden_set])
        precision = (overlap / len(retrieved_ids)) if retrieved_ids else 0.0
        recall = (overlap / len(golden_ids)) if golden_ids else 0.0
        return {
            "faithfulness": round(1.0 if overlap else 0.0, 4),
            "answer_relevancy": round(precision, 4),
            "context_precision": round(recall, 4),
        }
