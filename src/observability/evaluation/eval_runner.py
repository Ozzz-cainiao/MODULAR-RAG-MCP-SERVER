"""Evaluation runner for golden test sets."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from core.query_engine import HybridSearch
from core.settings import Settings
from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator


@dataclass(slots=True)
class EvalCaseResult:
    query: str
    retrieved_ids: list[str]
    expected_ids: list[str]
    metrics: dict[str, float]


@dataclass(slots=True)
class EvalReport:
    hit_rate: float
    mrr: float
    cases: list[EvalCaseResult]


class EvalRunner:
    def __init__(
        self,
        settings: Settings,
        hybrid_search: HybridSearch,
        evaluator: BaseEvaluator | None = None,
    ) -> None:
        self._settings = settings
        self._hybrid_search = hybrid_search
        self._evaluator = evaluator or CustomEvaluator(settings)

    def run(self, test_set_path: str) -> EvalReport:
        payload = json.loads(Path(test_set_path).read_text(encoding="utf-8"))
        cases: list[EvalCaseResult] = []
        aggregate_hit = 0.0
        aggregate_mrr = 0.0

        for case in payload.get("test_cases", []):
            query = str(case["query"])
            expected_ids = [str(item) for item in case.get("expected_chunk_ids", [])]
            search_result = self._hybrid_search.search(query, top_k=self._settings.retrieval.top_k)
            retrieved_ids = [result.chunk_id for result in search_result.fused_results]
            metrics = self._evaluator.evaluate(query, retrieved_ids, expected_ids)
            aggregate_hit += metrics.get("hit_rate", 0.0)
            aggregate_mrr += metrics.get("mrr", 0.0)
            cases.append(
                EvalCaseResult(
                    query=query,
                    retrieved_ids=retrieved_ids,
                    expected_ids=expected_ids,
                    metrics=metrics,
                )
            )

        total = len(cases) or 1
        return EvalReport(
            hit_rate=round(aggregate_hit / total, 4),
            mrr=round(aggregate_mrr / total, 4),
            cases=cases,
        )
