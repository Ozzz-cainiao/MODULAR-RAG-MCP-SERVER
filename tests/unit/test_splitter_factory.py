"""SplitterFactory 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.splitter.base_splitter import BaseSplitter, TraceContext
from libs.splitter.splitter_factory import SplitterFactory


class FakeRecursiveSplitter(BaseSplitter):
    """用于测试的 Fake Recursive Splitter。"""

    def split_text(self, text: str, trace: TraceContext | None = None) -> list[str]:
        """按空格切分文本，模拟递归切分。"""

        return text.split(" ")


class FakeFixedSplitter(BaseSplitter):
    """用于测试的 Fake Fixed Splitter。"""

    def split_text(self, text: str, trace: TraceContext | None = None) -> list[str]:
        """按固定长度 3 切分文本。"""

        return [text[index : index + 3] for index in range(0, len(text), 3)]


def _build_settings(provider: str) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider=provider),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_splitter_factory_create_when_provider_registered_then_return_recursive_splitter() -> None:
    """已注册 provider 时应返回对应 Splitter 实现。"""

    provider = "fake-recursive-b3"
    SplitterFactory.register(provider, FakeRecursiveSplitter)
    settings = _build_settings(provider)

    splitter = SplitterFactory.create(settings)

    assert isinstance(splitter, FakeRecursiveSplitter)
    assert splitter.split_text("a b c") == ["a", "b", "c"]


def test_splitter_factory_create_when_another_provider_registered_then_return_fixed_splitter() -> None:
    """不同 provider 应路由到不同 Splitter 实现。"""

    provider = "fake-fixed-b3"
    SplitterFactory.register(provider, FakeFixedSplitter)
    settings = _build_settings(provider)

    splitter = SplitterFactory.create(settings)

    assert isinstance(splitter, FakeFixedSplitter)
    assert splitter.split_text("abcdefg") == ["abc", "def", "g"]


def test_splitter_factory_create_when_provider_missing_then_raise_readable_error() -> None:
    """未注册 provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-splitter")

    with pytest.raises(ValueError, match="not-registered-splitter"):
        SplitterFactory.create(settings)

