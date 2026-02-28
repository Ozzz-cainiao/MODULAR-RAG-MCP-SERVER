"""OpenAI-compatible LLM provider 冒烟测试。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.llm.azure_llm import AzureLLM
from libs.llm.deepseek_llm import DeepSeekLLM
from libs.llm.llm_factory import LLMFactory
from libs.llm.openai_llm import OpenAILLM


ProviderClass = type[OpenAILLM] | type[AzureLLM] | type[DeepSeekLLM]


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


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAILLM),
        ("azure", AzureLLM),
        ("deepseek", DeepSeekLLM),
    ],
)
def test_llm_factory_create_when_provider_supported_then_route_correctly(
    provider: str,
    provider_class: ProviderClass,
) -> None:
    """配置不同 provider 时，工厂应路由到正确实现。"""

    settings = _build_settings(provider)

    llm = LLMFactory.create(settings)

    assert isinstance(llm, provider_class)


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAILLM),
        ("azure", AzureLLM),
        ("deepseek", DeepSeekLLM),
    ],
)
def test_provider_chat_when_input_shape_invalid_then_raise_readable_error(
    provider: str,
    provider_class: ProviderClass,
) -> None:
    """输入消息 shape 非法时应抛出可读错误。"""

    llm = provider_class(_build_settings(provider))

    with pytest.raises(ValueError, match=provider):
        llm.chat([{"role": "user"}])


@pytest.mark.parametrize(
    ("provider", "provider_class"),
    [
        ("openai", OpenAILLM),
        ("azure", AzureLLM),
        ("deepseek", DeepSeekLLM),
    ],
)
def test_provider_chat_when_mock_response_ok_then_return_content(
    provider: str,
    provider_class: ProviderClass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mock 成功响应时应返回文本内容。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": f"ok-{provider}",
                    }
                }
            ]
        }

    monkeypatch.setattr(provider_class, "_post_chat", _mock_post_chat)
    llm = provider_class(_build_settings(provider))

    output = llm.chat([{"role": "user", "content": "你好"}])

    assert output == f"ok-{provider}"


@pytest.mark.parametrize(
    ("provider", "provider_class", "error_factory"),
    [
        ("openai", OpenAILLM, TimeoutError),
        ("azure", AzureLLM, ConnectionError),
        ("deepseek", DeepSeekLLM, RuntimeError),
    ],
)
def test_provider_chat_when_transport_raises_then_raise_readable_runtime_error(
    provider: str,
    provider_class: ProviderClass,
    error_factory: Callable[[str], Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """底层调用异常时应抛出包含 provider 与错误类型的可读错误。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        raise error_factory("mock transport failure")

    monkeypatch.setattr(provider_class, "_post_chat", _mock_post_chat)
    llm = provider_class(_build_settings(provider))

    error_type = error_factory.__name__
    with pytest.raises(RuntimeError, match=f"{provider} chat failed: {error_type}"):
        llm.chat([{"role": "user", "content": "你好"}])

