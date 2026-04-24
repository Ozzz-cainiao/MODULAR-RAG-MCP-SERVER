"""Unit tests for DenseEncoder."""

from __future__ import annotations

from core.settings import (
    IngestionSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.trace import TraceContext
from core.types import Chunk
from ingestion.embedding.dense_encoder import DenseEncoder
from libs.embedding.base_embedding import BaseEmbedding, TraceContext as EmbeddingTraceContext


class FakeEmbedding(BaseEmbedding):
    """Fake embedding backend for DenseEncoder tests."""

    def __init__(self, settings: Settings, vectors: list[list[float]]) -> None:
        super().__init__(settings)
        self._vectors = vectors
        self.calls: list[tuple[list[str], EmbeddingTraceContext | None]] = []

    def embed(
        self,
        texts: list[str],
        trace: EmbeddingTraceContext | None = None,
    ) -> list[list[float]]:
        self.calls.append((texts, trace))
        return self._vectors


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


def _build_chunks() -> list[Chunk]:
    texts = ["第一段文本", "第二段文本"]
    chunks: list[Chunk] = []
    for index, text in enumerate(texts):
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


def test_dense_encoder_encode_when_chunks_valid_then_return_vectors_in_order() -> None:
    """应按输入顺序返回向量。"""

    settings = _build_settings()
    embedding = FakeEmbedding(settings, vectors=[[0.1, 0.2], [0.3, 0.4]])
    encoder = DenseEncoder(settings, embedding=embedding)

    vectors = encoder.encode(_build_chunks())

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert embedding.calls[0][0] == ["第一段文本", "第二段文本"]


def test_dense_encoder_encode_when_chunks_empty_then_return_empty_list() -> None:
    """空输入应直接返回空列表。"""

    settings = _build_settings()
    encoder = DenseEncoder(settings, embedding=FakeEmbedding(settings, vectors=[]))

    assert encoder.encode([]) == []


def test_dense_encoder_encode_when_vector_count_mismatch_then_raise_readable_error() -> None:
    """向量数量不匹配时应抛出可读错误。"""

    settings = _build_settings()
    encoder = DenseEncoder(settings, embedding=FakeEmbedding(settings, vectors=[[0.1, 0.2]]))

    try:
        encoder.encode(_build_chunks())
    except ValueError as error:
        assert "dense vector count mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError for vector count mismatch")


def test_dense_encoder_encode_when_vector_dimensions_inconsistent_then_raise() -> None:
    """向量维度不一致时应抛出错误。"""

    settings = _build_settings()
    encoder = DenseEncoder(
        settings,
        embedding=FakeEmbedding(settings, vectors=[[0.1, 0.2], [0.3]]),
    )

    try:
        encoder.encode(_build_chunks())
    except ValueError as error:
        assert "dense vector dimension mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError for dimension mismatch")


def test_dense_encoder_encode_when_trace_provided_then_forward_and_record_stage() -> None:
    """Trace 应传递给 embedding，并记录 dense_encoder 阶段。"""

    settings = _build_settings()
    embedding = FakeEmbedding(settings, vectors=[[0.1, 0.2], [0.3, 0.4]])
    encoder = DenseEncoder(settings, embedding=embedding)
    trace = TraceContext()

    encoder.encode(_build_chunks(), trace=trace)

    assert embedding.calls[0][1] is trace
    assert trace.stages[-1].name == "dense_encoder"
    assert trace.stages[-1].metadata["chunk_count"] == 2
    assert trace.stages[-1].metadata["dimension"] == 2
