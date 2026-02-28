"""OpenAI LLM 适配器实现。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from urllib.request import Request, urlopen

from core.settings import Settings
from libs.llm.base_llm import BaseLLM, Message


class OpenAILLM(BaseLLM):
    """OpenAI Chat Completions 适配器。"""

    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        """初始化 OpenAI LLM。"""

        super().__init__(settings)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def chat(self, messages: Sequence[Message]) -> str:
        """调用 OpenAI Chat Completions 并返回文本。"""

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
        """发送 HTTP 请求到 OpenAI 接口。"""

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        return _post_json(url=url, headers=headers, payload=payload)


def _validate_messages(messages: Sequence[Message], provider: str) -> list[dict[str, str]]:
    """校验消息列表的输入 shape。"""

    if not isinstance(messages, Sequence):
        raise ValueError(f"{provider} messages 必须是 Sequence")

    normalized: list[dict[str, str]] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"{provider} messages[{index}] 必须是 dict")

        role = message.get("role")
        content = message.get("content")

        if not isinstance(role, str) or not role.strip():
            raise ValueError(f"{provider} messages[{index}].role 必须是非空字符串")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{provider} messages[{index}].content 必须是非空字符串")

        normalized.append({"role": role, "content": content})

    if not normalized:
        raise ValueError(f"{provider} messages 不能为空")

    return normalized


def _extract_content(response: Mapping[str, object], provider: str) -> str:
    """从响应体提取首条回复文本。"""

    choices = response.get("choices") if isinstance(response, Mapping) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"{provider} 响应缺少 choices")

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise ValueError(f"{provider} 响应 choices[0] 格式非法")

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise ValueError(f"{provider} 响应缺少 message")

    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError(f"{provider} 响应缺少 content")

    return content


def _post_json(url: str, headers: dict[str, str], payload: dict[str, object]) -> Mapping[str, object]:
    """发送 JSON POST 请求并解析响应。"""

    request_headers = {"Content-Type": "application/json", **headers}
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        response_text = response.read().decode("utf-8")

    parsed = json.loads(response_text)
    if not isinstance(parsed, Mapping):
        raise ValueError("响应体必须是 JSON 对象")
    return parsed
