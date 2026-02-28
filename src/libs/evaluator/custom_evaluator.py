"""自定义轻量 Evaluator 实现。"""

from __future__ import annotations

from libs.evaluator.base_evaluator import BaseEvaluator, EvaluationMetrics, TraceContext


class CustomEvaluator(BaseEvaluator):
    """最小可用评估器。

    当前提供 `hit_rate` 与 `mrr` 两个稳定指标。
    """

    def evaluate(
        self,
        query: str,
        retrieved_ids: list[str],
        golden_ids: list[str],
        trace: TraceContext | None = None,
    ) -> EvaluationMetrics:
        """计算 hit_rate 与 mrr。

        参数:
            query: 用户查询文本。
            retrieved_ids: 检索返回 ID 列表。
            golden_ids: 标准答案 ID 列表。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            包含 `hit_rate`、`mrr` 的指标字典。
        """

        golden_set = set(golden_ids)
        has_hit = any(candidate_id in golden_set for candidate_id in retrieved_ids)
        hit_rate = 1.0 if has_hit else 0.0

        reciprocal_rank = 0.0
        for index, candidate_id in enumerate(retrieved_ids, start=1):
            if candidate_id in golden_set:
                reciprocal_rank = 1.0 / float(index)
                break

        return {
            "hit_rate": hit_rate,
            "mrr": reciprocal_rank,
        }

