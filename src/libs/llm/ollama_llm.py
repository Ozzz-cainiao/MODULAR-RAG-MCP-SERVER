"""Ollama LLM 适配器实现。"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from core.settings import Settings
from libs.llm.base_llm import BaseLLM, Message
from libs.llm.openai_llm import _post_json, _validate_messages


class OllamaLLM(BaseLLM):
    """Ollama 本地 Chat 适配器。"""

    provider_name = "ollama"

    def __init__(self, settings: Settings) -> None:
        """初始化 Ollama LLM。"""

        super().__init__(settings)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1")

    def chat(self, messages: Sequence[Message]) -> str:
        """调用 Ollama Chat 接口并返回文本。"""

        normalized_messages = _validate_messages(messages, self.provider_name)
        payload = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
        }

        try:
            response = self._post_chat(payload)
            return _extract_ollama_content(response, self.provider_name)
        except ValueError:
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise RuntimeError(f"{self.provider_name} chat failed: {error_type}: {error}") from error

    def _post_chat(self, payload: dict[str, object]) -> Mapping[str, object]:
        """发送 HTTP 请求到 Ollama 接口。"""

        url = f"{self.base_url}/api/chat"
        return _post_json(url=url, headers={}, payload=payload)


def _extract_ollama_content(response: Mapping[str, object], provider: str) -> str:
    """从 Ollama 响应中提取回复文本。"""

    if not isinstance(response, Mapping):
        raise ValueError(f"{provider} 响应格式非法")

    message = response.get("message")
    if not isinstance(message, Mapping):
        raise ValueError(f"{provider} 响应缺少 message")

    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{provider} 响应缺少 content")

    return content

