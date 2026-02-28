"""DeepSeek LLM 适配器实现。"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from core.settings import Settings
from libs.llm.base_llm import BaseLLM, Message
from libs.llm.openai_llm import _extract_content, _post_json, _validate_messages


class DeepSeekLLM(BaseLLM):
    """DeepSeek OpenAI-compatible Chat 适配器。"""

    provider_name = "deepseek"

    def __init__(self, settings: Settings) -> None:
        """初始化 DeepSeek LLM。"""

        super().__init__(settings)
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")

    def chat(self, messages: Sequence[Message]) -> str:
        """调用 DeepSeek Chat Completions 并返回文本。"""

        normalized_messages = _validate_messages(messages, self.provider_name)
        payload = {
            "model": self.model,
            "messages": normalized_messages,
        }

        try:
            response = self._post_chat(payload)
            return _extract_content(response, self.provider_name)
        except ValueError:
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise RuntimeError(f"{self.provider_name} chat failed: {error_type}: {error}") from error

    def _post_chat(self, payload: dict[str, object]) -> Mapping[str, object]:
        """发送 HTTP 请求到 DeepSeek 接口。"""

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return _post_json(url=url, headers=headers, payload=payload)

