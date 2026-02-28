"""Azure OpenAI LLM 适配器实现。"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from core.settings import Settings
from libs.llm.base_llm import BaseLLM, Message
from libs.llm.openai_llm import _extract_content, _post_json, _validate_messages


class AzureLLM(BaseLLM):
    """Azure OpenAI Chat Completions 适配器。"""

    provider_name = "azure"

    def __init__(self, settings: Settings) -> None:
        """初始化 Azure OpenAI LLM。"""

        super().__init__(settings)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://example-resource.openai.azure.com")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

    def chat(self, messages: Sequence[Message]) -> str:
        """调用 Azure OpenAI Chat Completions 并返回文本。"""

        normalized_messages = _validate_messages(messages, self.provider_name)
        payload = {
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
        """发送 HTTP 请求到 Azure OpenAI 接口。"""

        normalized_endpoint = self.endpoint.rstrip("/")
        url = (
            f"{normalized_endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key}
        return _post_json(url=url, headers=headers, payload=payload)

