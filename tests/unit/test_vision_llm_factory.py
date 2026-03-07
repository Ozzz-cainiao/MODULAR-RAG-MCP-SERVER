"""Vision LLM Factory 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse, TraceContext
from libs.llm.llm_factory import LLMFactory


class FakeVisionLLM(BaseVisionLLM):
    """用于测试的 Fake Vision LLM。"""

    def chat_with_image(
        self,
        text: str,
        image_input: str | bytes,
        trace: TraceContext | None = None,
    ) -> ChatResponse:
        """返回固定响应，用于验证路由。"""

        if isinstance(image_input, bytes):
            image_tag = "bytes"
        else:
            image_tag = "path"
        return {"text": f"{text}-{image_tag}"}


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider=provider),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_llm_factory_create_vision_llm_when_registered_then_return_fake() -> None:
    """已注册 Vision provider 时应返回对应实例。"""

    provider = "fake-vision-b8"
    LLMFactory.register_vision_llm(provider, FakeVisionLLM)
    settings = _build_settings(provider)

    vision_llm = LLMFactory.create_vision_llm(settings)

    assert isinstance(vision_llm, FakeVisionLLM)
    assert vision_llm.chat_with_image("hello", b"img") == {"text": "hello-bytes"}


def test_llm_factory_create_vision_llm_when_missing_then_raise_readable_error() -> None:
    """未注册 Vision provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-vision")

    with pytest.raises(ValueError, match="not-registered-vision"):
        LLMFactory.create_vision_llm(settings)
