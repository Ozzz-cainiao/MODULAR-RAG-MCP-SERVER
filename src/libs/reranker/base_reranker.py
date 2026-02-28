"""Reranker 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any
RerankCandidate: TypeAlias = dict[str, Any]


class BaseReranker(ABC):
    """Reranker 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Reranker 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        trace: TraceContext | None = None,
    ) -> list[RerankCandidate]:
        """按 query 对候选结果重排。

        参数:
            query: 用户查询文本。
            candidates: 待重排候选集合。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            重排后的候选集合。
        """

