"""Ollama LLM 单元测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.llm.llm_factory import LLMFactory
from libs.llm.ollama_llm import OllamaLLM


def _build_settings(provider: str = "ollama") -> Settings:
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


def test_llm_factory_create_when_provider_ollama_then_return_ollama_llm() -> None:
    """provider=ollama 时工厂应返回 OllamaLLM。"""

    llm = LLMFactory.create(_build_settings("ollama"))

    assert isinstance(llm, OllamaLLM)


def test_ollama_chat_when_message_shape_invalid_then_raise_readable_error() -> None:
    """输入消息 shape 非法时应抛出可读错误。"""

    llm = OllamaLLM(_build_settings())

    with pytest.raises(ValueError, match="ollama"):
        llm.chat([{"role": "user"}])


def test_ollama_chat_when_mock_response_ok_then_return_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mock 成功响应时应返回文本。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "message": {
                "role": "assistant",
                "content": "hello from ollama",
            }
        }

    monkeypatch.setattr(OllamaLLM, "_post_chat", _mock_post_chat)
    llm = OllamaLLM(_build_settings())

    output = llm.chat([{"role": "user", "content": "你好"}])

    assert output == "hello from ollama"


@pytest.mark.parametrize("error_type", [ConnectionError, TimeoutError])
def test_ollama_chat_when_transport_fails_then_raise_readable_runtime_error(
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """连接失败或超时时应抛出可读错误且不泄露敏感配置。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        raise error_type("mock transport failure")

    monkeypatch.setattr(OllamaLLM, "_post_chat", _mock_post_chat)
    llm = OllamaLLM(_build_settings())

    with pytest.raises(RuntimeError, match=f"ollama chat failed: {error_type.__name__}") as exc_info:
        llm.chat([{"role": "user", "content": "测试"}])

    message = str(exc_info.value)
    assert "api_key" not in message
    assert "OLLAMA_API_KEY" not in message

