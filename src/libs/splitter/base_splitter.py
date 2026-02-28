"""Splitter 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any


class BaseSplitter(ABC):
    """Splitter 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Splitter 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def split_text(
        self,
        text: str,
        trace: TraceContext | None = None,
    ) -> list[str]:
        """执行文本切分。

        参数:
            text: 待切分文本。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            切分后的文本块列表。
        """

