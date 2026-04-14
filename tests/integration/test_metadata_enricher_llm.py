"""MetadataEnricher LLM 集成测试。"""

from __future__ import annotations

import os

import pytest

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


def _build_settings() -> Settings:
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
                use_llm=True,
                prompt_path="config/prompts/metadata_enricher.txt",
            ),
        ),
    )


@pytest.mark.integration
def test_metadata_enricher_llm_when_openai_configured_then_enrich() -> None:
    """有 OPENAI_API_KEY 时应完成真实 LLM 调用。"""

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("缺少 OPENAI_API_KEY，跳过集成测试")

    settings = _build_settings()
    enricher = MetadataEnricher(settings)
    chunk = Chunk(
        id="chunk-meta-llm",
        text="This is a chunk that needs metadata enrichment.",
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "sample"},
        start_offset=0,
        end_offset=48,
        source_ref="doc-meta",
    )

    result = enricher.transform([chunk])[0]

    assert result.metadata.get("title")
    assert result.metadata.get("summary")
    assert result.metadata.get("tags")
