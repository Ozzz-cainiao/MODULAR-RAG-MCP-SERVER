"""LLM 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from core.settings import Settings


Message = dict[str, str]


class BaseLLM(ABC):
    """LLM 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 LLM 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def chat(self, messages: Sequence[Message]) -> str:
        """执行对话并返回文本结果。

        参数:
            messages: 对话消息列表。

        返回:
            模型返回文本。
        """

