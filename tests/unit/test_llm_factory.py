"""LLMFactory 单元测试。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.llm.base_llm import BaseLLM, Message
from libs.llm.llm_factory import LLMFactory


class FakeLLM(BaseLLM):
    """用于测试的 Fake LLM 实现。"""

    def chat(self, messages: Sequence[Message]) -> str:
        """返回固定文本，便于断言工厂路由结果。"""

        return f"fake:{len(messages)}"


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider=provider),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_llm_factory_create_when_provider_registered_then_return_fake_llm() -> None:
    """已注册 provider 时应返回对应实现。"""

    provider = "fake-b1"
    LLMFactory.register(provider, FakeLLM)
    settings = _build_settings(provider)

    llm = LLMFactory.create(settings)

    assert isinstance(llm, FakeLLM)
    assert llm.chat([{"role": "user", "content": "hi"}]) == "fake:1"


def test_llm_factory_create_when_provider_missing_then_raise_readable_error() -> None:
    """未注册 provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-provider")

    with pytest.raises(ValueError, match="not-registered-provider"):
        LLMFactory.create(settings)
