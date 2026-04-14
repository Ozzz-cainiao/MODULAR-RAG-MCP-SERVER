"""Loader 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.settings import Settings
from core.types import Document


class BaseLoader(ABC):
    """Loader 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Loader 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def load(self, path: str) -> Document:
        """加载源文件并转换为统一文档对象。

        参数:
            path: 待加载文件路径。

        返回:
            满足核心契约的 `Document` 对象。
        """

