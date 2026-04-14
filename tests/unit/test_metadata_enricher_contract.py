"""MetadataEnricher 契约测试。"""

from __future__ import annotations

from core.settings import (
    ChunkRefinerSettings,
    IngestionSettings,
    MetadataEnricherSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
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
