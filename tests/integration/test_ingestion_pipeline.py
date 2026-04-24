"""Integration tests for the ingestion pipeline MVP."""

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
from ingestion.pipeline import IngestionPipeline, PipelineError
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.base_embedding import TraceContext as EmbeddingTraceContext


class FakeLoader:
    """Deterministic loader for pipeline integration tests."""

    def __init__(self, with_images: bool = False) -> None:
        self._with_images = with_images

    def load(self, path: str) -> Document:
        metadata = {
            "source_path": str(Path(path).resolve()),
            "doc_type": "pdf",
            "title": "fake-doc",
            "images": [],
        }
        text = "# 标题\n\n这是一个用于 pipeline 集成测试的文档。"
        if self._with_images:
            image_path = Path(path).parent / "fake-image.png"
            image_path.write_bytes(b"fake-image")
            metadata["images"] = [
                {
                    "id": "img-001",
                    "path": str(image_path),
                    "text_offset": len(text),
                    "text_length": 0,
                    "page": 1,
                }
            ]
            text += "\n\n[IMAGE: img-001]"
        return Document(id="doc-001", text=text, metadata=metadata)


class FakeEmbedding(BaseEmbedding):
    """Deterministic embedding backend for pipeline integration tests."""

    def embed(
        self,
        texts: list[str],
        trace: EmbeddingTraceContext | None = None,
    ) -> list[list[float]]:
        return [[float(index), float(len(text))] for index, text in enumerate(texts)]


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


def _build_pipeline(tmp_path: Path, monkeypatch, loader: FakeLoader) -> IngestionPipeline:
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(tmp_path / "chroma"))
    settings = _build_settings()
    pipeline = IngestionPipeline(
        settings,
        loader=loader,
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


def test_ingestion_pipeline_when_simple_pdf_then_produce_all_outputs(tmp_path: Path, monkeypatch) -> None:
    """简单文档应跑通 load->split->transform->encode->store 全流程。"""

    fixture_path = tmp_path / "simple.pdf"
    fixture_path.write_bytes(b"%PDF-1.4 fake")
    pipeline = _build_pipeline(tmp_path, monkeypatch, loader=FakeLoader(with_images=True))

    trace = TraceContext(trace_type="ingestion")
    result = pipeline.run(str(fixture_path), collection="test-col", trace=trace)

    assert result.skipped is False
    assert result.chunk_count > 0
    assert result.dense_vector_count == result.chunk_count
    assert result.sparse_vector_count == result.chunk_count
    assert len(result.vector_ids) == result.chunk_count
    assert (tmp_path / "chroma" / "records.json").exists()
    assert (tmp_path / "bm25" / "bm25_index.pkl").exists()
    assert result.stored_image_paths
    assert Path(result.stored_image_paths[0]).exists()
    assert trace.trace_type == "ingestion"
    stage_names = [stage.name for stage in trace.stages]
    assert stage_names[:5] == ["integrity", "load", "split", "chunk_refiner", "chunk_refiner_llm"] or stage_names[:4] == ["integrity", "load", "split", "chunk_refiner"]
    assert "transform" in stage_names
    assert "embed" in stage_names
    assert "upsert" in stage_names
    for stage in trace.stages:
        if stage.name in {"load", "split", "transform", "embed", "upsert"}:
            assert "elapsed_ms" in stage.metadata


def test_ingestion_pipeline_when_repeated_without_force_then_skip(tmp_path: Path, monkeypatch) -> None:
    """重复 ingestion 且文件未变更时应跳过。"""

    fixture_path = tmp_path / "simple.pdf"
    fixture_path.write_bytes(b"%PDF-1.4 fake")
    pipeline = _build_pipeline(tmp_path, monkeypatch, loader=FakeLoader())

    first = pipeline.run(str(fixture_path), collection="test-col")
    second = pipeline.run(str(fixture_path), collection="test-col")

    assert first.skipped is False
    assert second.skipped is True


def test_ingestion_pipeline_when_loader_fails_then_raise_clear_pipeline_error(tmp_path: Path) -> None:
    """阶段失败时应抛出清晰异常。"""

    fixture_path = tmp_path / "simple.pdf"
    fixture_path.write_bytes(b"%PDF-1.4 fake")

    class BrokenLoader:
        def load(self, path: str) -> Document:
            raise RuntimeError("load failed")

    pipeline = IngestionPipeline(_build_settings(), loader=BrokenLoader())
    pipeline._integrity_checker = pipeline._integrity_checker.__class__(
        db_path=str(tmp_path / "db" / "ingestion_history.db")
    )

    try:
        pipeline.run(str(fixture_path), collection="test-col")
    except PipelineError as error:
        assert "Pipeline failed" in str(error)
        assert "load failed" in str(error)
    else:
        raise AssertionError("Expected PipelineError when loader fails")
