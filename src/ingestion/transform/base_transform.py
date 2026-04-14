"""Transform 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.types import Chunk


TraceContext: TypeAlias = Any


class BaseTransform(ABC):
    """Transform 适配器基类。"""

    @abstractmethod
    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """对 Chunk 列表执行转换。"""

