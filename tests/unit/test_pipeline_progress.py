"""Unit tests for ingestion pipeline progress callbacks."""

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
from core.types import Document
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.embedding.dense_encoder import DenseEncoder
from ingestion.embedding.sparse_encoder import SparseEncoder
from ingestion.pipeline import IngestionPipeline
from libs.embedding.base_embedding import BaseEmbedding


class FakeLoader:
    def load(self, path: str) -> Document:
        return Document(
            id="doc-001",
            text="progress test document",
            metadata={
                "source_path": str(Path(path).resolve()),
                "doc_type": "pdf",
                "title": "Progress",
                "images": [],
            },
        )


class FakeEmbedding(BaseEmbedding):
    def embed(self, texts: list[str], trace=None) -> list[list[float]]:
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider=""),
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
                use_llm=False,
                prompt_path="config/prompts/metadata_enricher.txt",
            ),
        ),
    )


def _build_pipeline(tmp_path: Path, monkeypatch) -> IngestionPipeline:
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(tmp_path / "chroma"))
    settings = _build_settings()
    pipeline = IngestionPipeline(
        settings,
        loader=FakeLoader(),
        batch_processor=BatchProcessor(
            dense_encoder=DenseEncoder(settings, embedding=FakeEmbedding(settings)),
            sparse_encoder=SparseEncoder(),
            batch_size=2,
        ),
    )
    pipeline._bm25_indexer = pipeline._bm25_indexer.__class__(persist_dir=str(tmp_path / "bm25"))
    pipeline._image_storage = pipeline._image_storage.__class__(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(tmp_path / "db" / "image_index.db"),
    )
    pipeline._integrity_checker = pipeline._integrity_checker.__class__(
        db_path=str(tmp_path / "db" / "ingestion_history.db")
    )
    return pipeline


def test_pipeline_run_when_on_progress_provided_then_emit_all_major_stages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fixture_path = tmp_path / "simple.pdf"
    fixture_path.write_bytes(b"%PDF-1.4 fake")
    pipeline = _build_pipeline(tmp_path, monkeypatch)
    calls: list[tuple[str, int, int]] = []

    pipeline.run(
        str(fixture_path),
        collection="test-col",
        trace=TraceContext(trace_type="ingestion"),
        on_progress=lambda stage, current, total: calls.append((stage, current, total)),
    )

    assert calls == [
        ("integrity", 1, 6),
        ("load", 2, 6),
        ("split", 3, 6),
        ("transform", 4, 6),
        ("embed", 5, 6),
        ("upsert", 6, 6),
    ]
