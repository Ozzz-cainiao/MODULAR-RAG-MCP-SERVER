"""ChunkRefiner 单元测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.settings import (
    ChunkRefinerSettings,
    IngestionSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.types import Chunk
from ingestion.transform.chunk_refiner import ChunkRefiner
from libs.llm.base_llm import BaseLLM


class FakeLLM(BaseLLM):
    """用于单元测试的 Fake LLM。"""

    def __init__(self, settings: Settings, response: str | None, raise_error: bool = False) -> None:
        super().__init__(settings)
        self._response = response
        self._raise_error = raise_error

    def chat(self, messages: list[dict[str, str]]) -> str:
        if self._raise_error:
            raise RuntimeError("fake llm error")
        return self._response or ""


def _build_settings(use_llm: bool = False) -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider="azure_openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
        ingestion=IngestionSettings(
            chunk_refiner=ChunkRefinerSettings(
                use_llm=use_llm,
                prompt_path="config/prompts/chunk_refinement.txt",
            )
        ),
    )


def _build_chunk(text: str) -> Chunk:
    return Chunk(
        id="chunk-001",
        text=text,
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=len(text),
        source_ref="doc-001",
    )


def _load_noisy_chunks() -> list[dict[str, Any]]:
    fixture_path = Path("tests/fixtures/noisy_chunks.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("payload", _load_noisy_chunks())
def test_chunk_refiner_rule_based_refine_when_noisy_then_cleanup(payload: dict[str, Any]) -> None:
    """规则模式应对噪声做清洗。"""

    settings = _build_settings(use_llm=False)
    refiner = ChunkRefiner(settings)
    chunk = _build_chunk(payload["input"])

    result = refiner.transform([chunk])[0]

    for expected in payload["expected_contains"]:
        assert expected in result.text
    for banned in payload["expected_not_contains"]:
        assert banned not in result.text
    assert result.metadata["refined_by"] == "rule"


def test_chunk_refiner_llm_refine_when_enabled_then_use_llm_output() -> None:
    """启用 LLM 时应使用 LLM 返回内容。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response="LLM refined text")
    refiner = ChunkRefiner(settings, llm=llm)
    chunk = _build_chunk("原始文本")

    result = refiner.transform([chunk])[0]

    assert result.text == "LLM refined text"
    assert result.metadata["refined_by"] == "llm"


def test_chunk_refiner_llm_refine_when_llm_fails_then_fallback_to_rule() -> None:
    """LLM 失败时应回退到规则结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response=None, raise_error=True)
    refiner = ChunkRefiner(settings, llm=llm)
    chunk = _build_chunk("保留文本")

    result = refiner.transform([chunk])[0]

    assert result.text == "保留文本"
    assert result.metadata["refined_by"] == "rule"
    assert result.metadata["refine_fallback_reason"] == "llm_failed_or_empty"
