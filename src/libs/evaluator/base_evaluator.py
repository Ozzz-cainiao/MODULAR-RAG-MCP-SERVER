"""Evaluator 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any
EvaluationMetrics: TypeAlias = dict[str, float]


class BaseEvaluator(ABC):
    """Evaluator 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Evaluator 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def evaluate(
        self,
        query: str,
        retrieved_ids: list[str],
        golden_ids: list[str],
        trace: TraceContext | None = None,
    ) -> EvaluationMetrics:
        """评估检索结果质量。

        参数:
            query: 用户查询文本。
            retrieved_ids: 检索返回 ID 列表。
            golden_ids: 标准答案 ID 列表。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            评估指标字典。
        """

