"""Azure Vision LLM 单元测试。"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.llm.azure_vision_llm import AzureVisionLLM
from libs.llm.llm_factory import LLMFactory


def _build_settings(provider: str = "azure") -> Settings:
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


def test_llm_factory_create_vision_llm_when_provider_azure_then_return_azure() -> None:
    """provider=azure 时工厂应返回 AzureVisionLLM。"""

    vision_llm = LLMFactory.create_vision_llm(_build_settings("azure"))

    assert isinstance(vision_llm, AzureVisionLLM)


def test_azure_vision_llm_chat_with_image_when_path_then_return_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """图片路径输入时应返回结构化文本。"""

    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"fake-image-bytes")

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        assert "messages" in payload
        return {"choices": [{"message": {"content": "ok-path"}}]}

    monkeypatch.setattr(AzureVisionLLM, "_post_chat", _mock_post_chat)
    vision_llm = AzureVisionLLM(_build_settings())

    response = vision_llm.chat_with_image("describe", str(image_path))

    assert response == {"text": "ok-path"}


def test_azure_vision_llm_chat_with_image_when_base64_then_return_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """base64 输入时应返回结构化文本。"""

    encoded = base64.b64encode(b"fake-image").decode("utf-8")

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        return {"choices": [{"message": {"content": "ok-base64"}}]}

    monkeypatch.setattr(AzureVisionLLM, "_post_chat", _mock_post_chat)
    vision_llm = AzureVisionLLM(_build_settings())

    response = vision_llm.chat_with_image("describe", encoded)

    assert response == {"text": "ok-base64"}


def test_azure_vision_llm_chat_with_image_when_error_payload_then_raise_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Azure error payload 时应抛出可读错误。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        return {"error": {"code": "BadRequest", "message": "invalid image"}}

    monkeypatch.setattr(AzureVisionLLM, "_post_chat", _mock_post_chat)
    vision_llm = AzureVisionLLM(_build_settings())

    with pytest.raises(ValueError, match="BadRequest"):
        vision_llm.chat_with_image("describe", b"fake")


def test_azure_vision_llm_chat_with_image_when_resize_needed_then_use_resize_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """图片过大时应触发压缩钩子。"""

    calls: dict[str, int] = {"count": 0}

    def _mock_resize(image_bytes: bytes, max_size: int) -> bytes:
        calls["count"] += 1
        return image_bytes

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        return {"choices": [{"message": {"content": "ok-resize"}}]}

    monkeypatch.setattr("libs.llm.azure_vision_llm._resize_image_bytes", _mock_resize)
    monkeypatch.setattr(AzureVisionLLM, "_post_chat", _mock_post_chat)

    vision_llm = AzureVisionLLM(_build_settings())
    response = vision_llm.chat_with_image("describe", b"fake-image")

    assert response == {"text": "ok-resize"}
    assert calls["count"] == 1


def test_azure_vision_llm_chat_with_image_when_invalid_base64_then_raise_error() -> None:
    """无效 base64 输入应抛出可读错误。"""

    vision_llm = AzureVisionLLM(_build_settings())

    with pytest.raises(ValueError, match="base64"):
        vision_llm.chat_with_image("describe", "not-base64")


def test_azure_vision_llm_chat_with_image_when_transport_failed_then_raise_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """传输异常时应抛出包含 provider 信息的错误。"""

    def _mock_post_chat(self, payload: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("timeout")

    monkeypatch.setattr(AzureVisionLLM, "_post_chat", _mock_post_chat)
    vision_llm = AzureVisionLLM(_build_settings())

    with pytest.raises(RuntimeError, match="azure vision chat failed: TimeoutError"):
        vision_llm.chat_with_image("describe", b"fake")
