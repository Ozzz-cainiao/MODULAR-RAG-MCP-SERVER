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
from core.trace import TraceContext
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


def test_chunk_refiner_llm_refine_when_response_empty_then_fallback_to_rule() -> None:
    """LLM 返回空字符串时应回退到规则结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response="")
    refiner = ChunkRefiner(settings, llm=llm)
    chunk = _build_chunk("保留文本")

    result = refiner.transform([chunk])[0]

    assert result.text == "保留文本"
    assert result.metadata["refined_by"] == "rule"
    assert result.metadata["refine_fallback_reason"] == "llm_failed_or_empty"


def test_chunk_refiner_when_prompt_missing_placeholder_then_append_text_placeholder(
    tmp_path: Path,
) -> None:
    """Prompt 文件缺少占位符时应自动追加。"""

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Refine this chunk.", encoding="utf-8")

    settings = _build_settings(use_llm=False)
    refiner = ChunkRefiner(settings, prompt_path=str(prompt_path))

    assert "{text}" in refiner._prompt_template
    assert refiner._prompt_template.endswith("\n\n{text}")


def test_chunk_refiner_when_prompt_missing_then_use_default_prompt() -> None:
    """Prompt 文件不存在时应使用默认模板。"""

    settings = _build_settings(use_llm=False)
    refiner = ChunkRefiner(settings, prompt_path="config/prompts/not-found.txt")

    assert "Refine the following chunk" in refiner._prompt_template
    assert "{text}" in refiner._prompt_template


def test_chunk_refiner_when_trace_provided_then_record_rule_and_llm_stages() -> None:
    """处理时应把规则阶段和 LLM 阶段写入 trace。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response="LLM refined text")
    refiner = ChunkRefiner(settings, llm=llm)
    trace = TraceContext()

    refiner.transform([_build_chunk("原始文本")], trace=trace)

    stage_names = [stage.name for stage in trace.stages]
    assert stage_names == ["chunk_refiner", "chunk_refiner_llm"]
    assert trace.stages[0].metadata["chunk_id"] == "chunk-001"
    assert trace.stages[1].metadata["status"] == "success"


def test_chunk_refiner_when_single_chunk_raises_then_other_chunks_continue(monkeypatch) -> None:
    """单个 chunk 处理异常不应中断整批转换。"""

    settings = _build_settings(use_llm=False)
    refiner = ChunkRefiner(settings)
    broken_chunk = Chunk(
        id="chunk-broken",
        text="broken",
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=6,
        source_ref="doc-001",
    )
    healthy_chunk = _build_chunk("保留文本")
    original_refine_single = refiner._refine_single

    def fake_refine_single(chunk: Chunk, trace: TraceContext | None) -> Chunk:
        if chunk.id == "chunk-broken":
            raise RuntimeError("boom")
        return original_refine_single(chunk, trace)

    monkeypatch.setattr(refiner, "_refine_single", fake_refine_single)

    results = refiner.transform([broken_chunk, healthy_chunk])

    assert results[0].text == "broken"
    assert results[0].metadata["refined_by"] == "error"
    assert results[0].metadata["refine_error"] == "RuntimeError"
    assert results[1].text == "保留文本"
    assert results[1].metadata["refined_by"] == "rule"
