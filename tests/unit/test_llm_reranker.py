"""LLMReranker 单元测试。"""

from __future__ import annotations

import json
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
from libs.reranker.llm_reranker import LLMReranker
from libs.reranker.reranker_factory import RerankerFactory


class FakeLLM(BaseLLM):
    """用于测试的 Fake LLM。"""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.output_text = ""
        self.error_to_raise: Exception | None = None
        self.last_messages: list[Message] = []

    def chat(self, messages: Sequence[Message]) -> str:
        self.last_messages = list(messages)
        if self.error_to_raise is not None:
            raise self.error_to_raise
        return self.output_text


def _build_settings(rerank_provider: str = "llm") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider=rerank_provider),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_reranker_factory_create_when_provider_llm_then_return_llm_reranker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """backend=llm 时工厂应返回 LLMReranker。"""

    fake_llm = FakeLLM(_build_settings())
    monkeypatch.setattr(LLMFactory, "create", lambda settings: fake_llm)

    reranker = RerankerFactory.create(_build_settings("llm"))

    assert isinstance(reranker, LLMReranker)


def test_llm_reranker_rerank_when_schema_valid_then_return_ranked_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 输出结构合法时应按 ranked_ids 重排。"""

    fake_llm = FakeLLM(_build_settings())
    fake_llm.output_text = json.dumps({"ranked_ids": ["c2", "c1"]}, ensure_ascii=False)
    monkeypatch.setattr(LLMFactory, "create", lambda settings: fake_llm)

    reranker = LLMReranker(_build_settings())
    candidates = [
        {"chunk_id": "c1", "text": "first", "metadata": {}},
        {"chunk_id": "c2", "text": "second", "metadata": {}},
    ]

    ranked = reranker.rerank(query="如何学习 RAG", candidates=candidates)

    assert [item["chunk_id"] for item in ranked] == ["c2", "c1"]


def test_llm_reranker_rerank_when_schema_invalid_then_raise_readable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 输出 schema 非法时应抛出可读错误。"""

    fake_llm = FakeLLM(_build_settings())
    fake_llm.output_text = json.dumps({"ids": ["c1", "c2"]}, ensure_ascii=False)
    monkeypatch.setattr(LLMFactory, "create", lambda settings: fake_llm)

    reranker = LLMReranker(_build_settings())

    with pytest.raises(ValueError, match="ranked_ids"):
        reranker.rerank(
            query="query",
            candidates=[
                {"chunk_id": "c1", "text": "first", "metadata": {}},
                {"chunk_id": "c2", "text": "second", "metadata": {}},
            ],
        )


def test_llm_reranker_rerank_when_llm_failed_then_return_fallback_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 失败时应返回可回退信号并保持原顺序。"""

    fake_llm = FakeLLM(_build_settings())
    fake_llm.error_to_raise = TimeoutError("mock timeout")
    monkeypatch.setattr(LLMFactory, "create", lambda settings: fake_llm)

    reranker = LLMReranker(_build_settings())
    candidates = [
        {"chunk_id": "c1", "text": "first", "metadata": {"source": "a"}},
        {"chunk_id": "c2", "text": "second", "metadata": {"source": "b"}},
    ]

    ranked = reranker.rerank(query="query", candidates=candidates)

    assert [item["chunk_id"] for item in ranked] == ["c1", "c2"]
    assert ranked[0]["metadata"]["rerank_fallback"] == "llm_failed"
    assert ranked[1]["metadata"]["rerank_fallback"] == "llm_failed"


def test_llm_reranker_rerank_when_prompt_injected_then_prompt_text_used(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试可注入替代 prompt 模板。"""

    prompt_path = tmp_path / "rerank_prompt.txt"
    prompt_path.write_text("CUSTOM-PROMPT\nquery={query}\nitems={candidates_json}", encoding="utf-8")
    monkeypatch.setenv("RERANK_PROMPT_PATH", str(prompt_path))

    fake_llm = FakeLLM(_build_settings())
    fake_llm.output_text = json.dumps({"ranked_ids": ["c1"]}, ensure_ascii=False)
    monkeypatch.setattr(LLMFactory, "create", lambda settings: fake_llm)

    reranker = LLMReranker(_build_settings())
    reranker.rerank(
        query="自定义 query",
        candidates=[{"chunk_id": "c1", "text": "only", "metadata": {}}],
    )

    assert any("CUSTOM-PROMPT" in message["content"] for message in fake_llm.last_messages)
