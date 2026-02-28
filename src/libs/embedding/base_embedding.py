"""Embedding 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any


class BaseEmbedding(ABC):
    """Embedding 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Embedding 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """执行批量文本向量化。

        参数:
            texts: 待向量化文本列表。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            二维向量结果列表。
        """

