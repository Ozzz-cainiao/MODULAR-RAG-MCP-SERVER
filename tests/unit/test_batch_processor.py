"""Unit tests for BatchProcessor."""

from __future__ import annotations

from core.settings import (
    IngestionSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.trace import TraceContext
from core.types import Chunk, SparseVector
from ingestion.embedding.batch_processor import BatchProcessor
from ingestion.embedding.dense_encoder import DenseEncoder
from ingestion.embedding.sparse_encoder import SparseEncoder
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.base_embedding import TraceContext as EmbeddingTraceContext


class FakeEmbedding(BaseEmbedding):
    """Fake embedding backend returning predictable vectors."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.calls: list[list[str]] = []

    def embed(
        self,
        texts: list[str],
        trace: EmbeddingTraceContext | None = None,
    ) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(index), float(len(text))] for index, text in enumerate(texts)]


class FakeSparseEncoder(SparseEncoder):
    """Sparse encoder test double that tracks batch calls."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(
        self,
        chunks: list[Chunk],
        trace: TraceContext | None = None,
    ) -> list[SparseVector]:
        self.calls.append([chunk.id for chunk in chunks])
        return [{chunk.id: 1.0} for chunk in chunks]


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider="azure"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
        ingestion=IngestionSettings(),
    )


def _build_chunks(count: int = 5) -> list[Chunk]:
    chunks: list[Chunk] = []
    for index in range(count):
        text = f"chunk text {index}"
        chunks.append(
            Chunk(
                id=f"chunk-{index}",
                text=text,
                metadata={"source_path": "sample.pdf", "doc_type": "pdf", "title": "样例"},
                start_offset=index * 10,
                end_offset=index * 10 + len(text),
                source_ref="doc-001",
            )
        )
    return chunks


def test_batch_processor_when_batch_size_two_and_five_chunks_then_split_into_three_batches() -> None:
    """batch_size=2, 5 chunks 时应切成 3 批且顺序稳定。"""

    settings = _build_settings()
    embedding = FakeEmbedding(settings)
    dense_encoder = DenseEncoder(settings, embedding=embedding)
    sparse_encoder = FakeSparseEncoder()
    processor = BatchProcessor(dense_encoder=dense_encoder, sparse_encoder=sparse_encoder, batch_size=2)

    result = processor.process(_build_chunks(5))

    assert embedding.calls == [
        ["chunk text 0", "chunk text 1"],
        ["chunk text 2", "chunk text 3"],
        ["chunk text 4"],
    ]
    assert sparse_encoder.calls == [
        ["chunk-0", "chunk-1"],
        ["chunk-2", "chunk-3"],
        ["chunk-4"],
    ]
    assert len(result.dense_vectors) == 5
    assert len(result.sparse_vectors) == 5
    assert result.sparse_vectors[0] == {"chunk-0": 1.0}
    assert result.sparse_vectors[-1] == {"chunk-4": 1.0}


def test_batch_processor_when_trace_provided_then_record_batch_stages() -> None:
    """应为每个批次记录 batch_processor trace。"""

    settings = _build_settings()
    processor = BatchProcessor(
        dense_encoder=DenseEncoder(settings, embedding=FakeEmbedding(settings)),
        sparse_encoder=FakeSparseEncoder(),
        batch_size=2,
    )
    trace = TraceContext()

    processor.process(_build_chunks(3), trace=trace)

    batch_stages = [stage for stage in trace.stages if stage.name == "batch_processor"]
    assert len(batch_stages) == 2
    assert batch_stages[0].metadata["batch_index"] == 0
    assert batch_stages[0].metadata["batch_size"] == 2
    assert "elapsed_ms" in batch_stages[0].metadata
    assert batch_stages[1].metadata["batch_index"] == 1
    assert batch_stages[1].metadata["batch_size"] == 1


def test_batch_processor_when_chunks_empty_then_return_empty_results() -> None:
    """空输入应返回空结果。"""

    settings = _build_settings()
    processor = BatchProcessor(
        dense_encoder=DenseEncoder(settings, embedding=FakeEmbedding(settings)),
        sparse_encoder=FakeSparseEncoder(),
    )

    result = processor.process([])

    assert result.dense_vectors == []
    assert result.sparse_vectors == []


def test_batch_processor_when_batch_size_invalid_then_raise_readable_error() -> None:
    """非法 batch_size 应抛出可读错误。"""

    settings = _build_settings()

    try:
        BatchProcessor(
            dense_encoder=DenseEncoder(settings, embedding=FakeEmbedding(settings)),
            sparse_encoder=FakeSparseEncoder(),
            batch_size=0,
        )
    except ValueError as error:
        assert "batch_size" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid batch_size")
