"""Vision LLM 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any
ChatResponse: TypeAlias = dict[str, str]


class BaseVisionLLM(ABC):
    """Vision LLM 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Vision LLM 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def chat_with_image(
        self,
        text: str,
        image_input: str | bytes,
        trace: TraceContext | None = None,
    ) -> ChatResponse:
        """执行多模态对话并返回结构化结果。

        参数:
            text: 文本提示词。
            image_input: 图片路径或图片 bytes，预留图片预处理扩展点。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            结构化响应结果（例如包含回答文本）。
        """
