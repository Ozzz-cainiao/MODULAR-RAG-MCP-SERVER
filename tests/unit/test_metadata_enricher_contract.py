"""MetadataEnricher 契约测试。"""

from __future__ import annotations

from pathlib import Path

from core.settings import (
    ChunkRefinerSettings,
    IngestionSettings,
    MetadataEnricherSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.trace import TraceContext
from core.types import Chunk
from ingestion.transform.metadata_enricher import MetadataEnricher
from libs.llm.base_llm import BaseLLM


class FakeLLM(BaseLLM):
    """用于测试的 Fake LLM。"""

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
                use_llm=False,
                prompt_path="config/prompts/chunk_refinement.txt",
            ),
            metadata_enricher=MetadataEnricherSettings(
                use_llm=use_llm,
                prompt_path="config/prompts/metadata_enricher.txt",
            ),
        ),
    )


def _build_chunk(text: str) -> Chunk:
    return Chunk(
        id="chunk-meta-001",
        text=text,
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=len(text),
        source_ref="doc-001",
    )


def test_metadata_enricher_rule_based_when_disabled_then_generate_fields() -> None:
    """规则模式应补齐 title/summary/tags。"""

    settings = _build_settings(use_llm=False)
    enricher = MetadataEnricher(settings)
    chunk = _build_chunk("这是一段用于测试的正文内容。")

    result = enricher.transform([chunk])[0]

    assert result.metadata["title"]
    assert result.metadata["summary"]
    assert result.metadata["tags"]
    assert result.metadata["metadata_enriched_by"] == "rule"


def test_metadata_enricher_llm_when_enabled_then_use_llm_output() -> None:
    """启用 LLM 时应使用 LLM 输出结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(
        settings,
        response='{"title": "标题", "summary": "摘要", "tags": ["tag1", "tag2"]}',
    )
    enricher = MetadataEnricher(settings, llm=llm)
    chunk = _build_chunk("原始内容")

    result = enricher.transform([chunk])[0]

    assert result.metadata["title"] == "标题"
    assert result.metadata["summary"] == "摘要"
    assert result.metadata["tags"] == ["tag1", "tag2"]
    assert result.metadata["metadata_enriched_by"] == "llm"


def test_metadata_enricher_llm_when_failed_then_fallback_to_rule() -> None:
    """LLM 失败时应回退到规则结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response=None, raise_error=True)
    enricher = MetadataEnricher(settings, llm=llm)
    chunk = _build_chunk("保留内容")

    result = enricher.transform([chunk])[0]

    assert result.metadata["metadata_enriched_by"] == "rule"
    assert result.metadata["metadata_enrich_fallback_reason"] == "llm_failed_or_invalid"


def test_metadata_enricher_llm_when_response_empty_then_fallback_to_rule() -> None:
    """LLM 返回空字符串时应回退到规则结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response="")
    enricher = MetadataEnricher(settings, llm=llm)

    result = enricher.transform([_build_chunk("保留内容")])[0]

    assert result.metadata["metadata_enriched_by"] == "rule"
    assert result.metadata["metadata_enrich_fallback_reason"] == "llm_failed_or_invalid"


def test_metadata_enricher_llm_when_response_invalid_json_then_fallback_to_rule() -> None:
    """LLM 返回非法 JSON 时应回退到规则结果。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(settings, response="not json")
    enricher = MetadataEnricher(settings, llm=llm)

    result = enricher.transform([_build_chunk("保留内容")])[0]

    assert result.metadata["metadata_enriched_by"] == "rule"
    assert result.metadata["metadata_enrich_fallback_reason"] == "llm_failed_or_invalid"


def test_metadata_enricher_when_prompt_missing_placeholder_then_append_text_placeholder(
    tmp_path: Path,
) -> None:
    """Prompt 文件缺少占位符时应自动追加。"""

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Generate metadata.", encoding="utf-8")

    settings = _build_settings(use_llm=False)
    enricher = MetadataEnricher(settings, prompt_path=str(prompt_path))

    assert "{text}" in enricher._prompt_template
    assert enricher._prompt_template.endswith("\n\n{text}")


def test_metadata_enricher_when_prompt_missing_then_use_default_prompt() -> None:
    """Prompt 文件不存在时应使用默认模板。"""

    settings = _build_settings(use_llm=False)
    enricher = MetadataEnricher(settings, prompt_path="config/prompts/not-found.txt")

    assert "Generate JSON with title, summary, tags for:" in enricher._prompt_template
    assert "{text}" in enricher._prompt_template


def test_metadata_enricher_when_trace_provided_then_record_rule_and_llm_stages() -> None:
    """处理时应把规则阶段和 LLM 阶段写入 trace。"""

    settings = _build_settings(use_llm=True)
    llm = FakeLLM(
        settings,
        response='{"title": "标题", "summary": "摘要", "tags": ["tag1", "tag2"]}',
    )
    enricher = MetadataEnricher(settings, llm=llm)
    trace = TraceContext()

    enricher.transform([_build_chunk("原始内容")], trace=trace)

    stage_names = [stage.name for stage in trace.stages]
    assert stage_names == ["metadata_enricher", "metadata_enricher_llm"]
    assert trace.stages[0].metadata["chunk_id"] == "chunk-meta-001"
    assert trace.stages[1].metadata["status"] == "success"
    assert trace.stages[1].metadata["tag_count"] == 2


def test_metadata_enricher_when_single_chunk_raises_then_other_chunks_continue(monkeypatch) -> None:
    """单个 chunk 处理异常不应中断整批转换。"""

    settings = _build_settings(use_llm=False)
    enricher = MetadataEnricher(settings)
    broken_chunk = Chunk(
        id="chunk-meta-broken",
        text="broken",
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=6,
        source_ref="doc-001",
    )
    healthy_chunk = _build_chunk("保留内容")
    original_enrich_single = enricher._enrich_single

    def fake_enrich_single(chunk: Chunk, trace: TraceContext | None) -> Chunk:
        if chunk.id == "chunk-meta-broken":
            raise RuntimeError("boom")
        return original_enrich_single(chunk, trace)

    monkeypatch.setattr(enricher, "_enrich_single", fake_enrich_single)

    results = enricher.transform([broken_chunk, healthy_chunk])

    assert results[0].text == "broken"
    assert results[0].metadata["metadata_enriched_by"] == "error"
    assert results[0].metadata["metadata_enrich_error"] == "RuntimeError"
    assert results[1].metadata["metadata_enriched_by"] == "rule"
