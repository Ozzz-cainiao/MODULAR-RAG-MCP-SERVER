"""Unit tests for VectorUpserter idempotency and ordering."""

from __future__ import annotations

from typing import Any

from core.settings import (
    IngestionSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.trace import TraceContext
from core.types import Chunk
from ingestion.storage.vector_upserter import VectorUpserter
from libs.vector_store.base_vector_store import BaseVectorStore, TraceContext as VectorTraceContext
from libs.vector_store.base_vector_store import VectorRecord


class FakeVectorStore(BaseVectorStore):
    """In-memory vector store test double."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.records: dict[str, VectorRecord] = {}
        self.calls: list[list[str]] = []

    def upsert(self, records: list[VectorRecord], trace: VectorTraceContext | None = None) -> None:
        self.calls.append([record["chunk_id"] for record in records])
        for record in records:
            self.records[record["chunk_id"]] = record

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: VectorTraceContext | None = None,
    ) -> list[dict[str, Any]]:
        return []

    def get_by_ids(
        self,
        chunk_ids: list[str],
        trace: VectorTraceContext | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": chunk_id,
                "score": 0.0,
                "text": str(record["text"]),
                "metadata": dict(record["metadata"]),
            }
            for chunk_id in chunk_ids
            if (record := self.records.get(chunk_id)) is not None
        ]


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


def _build_chunk(text: str, chunk_index: int = 0) -> Chunk:
    return Chunk(
        id=f"input-chunk-{chunk_index}",
        text=text,
        metadata={"source_path": "sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=chunk_index * 10,
        end_offset=chunk_index * 10 + len(text),
        source_ref="doc-001",
    )


def test_vector_upserter_when_same_chunk_twice_then_generate_same_id() -> None:
    """同一 chunk 两次 upsert 应产生相同 id。"""

    settings = _build_settings()
    store = FakeVectorStore(settings)
    upserter = VectorUpserter(settings, vector_store=store)
    chunk = _build_chunk("same content")

    first_ids = upserter.upsert([chunk], [[0.1, 0.2]])
    second_ids = upserter.upsert([chunk], [[0.1, 0.2]])

    assert first_ids == second_ids
    assert len(store.records) == 1


def test_vector_upserter_when_content_changes_then_generate_different_id() -> None:
    """内容变化时稳定 id 应变化。"""

    settings = _build_settings()
    store = FakeVectorStore(settings)
    upserter = VectorUpserter(settings, vector_store=store)

    first_ids = upserter.upsert([_build_chunk("content a")], [[0.1, 0.2]])
    second_ids = upserter.upsert([_build_chunk("content b")], [[0.1, 0.2]])

    assert first_ids != second_ids


def test_vector_upserter_when_batch_upsert_then_preserve_input_order() -> None:
    """批量 upsert 返回 id 顺序应与输入顺序一致。"""

    settings = _build_settings()
    store = FakeVectorStore(settings)
    upserter = VectorUpserter(settings, vector_store=store)
    chunks = [_build_chunk("first", 0), _build_chunk("second", 1), _build_chunk("third", 2)]

    chunk_ids = upserter.upsert(chunks, [[0.1], [0.2], [0.3]])

    assert store.calls[0] == chunk_ids
    assert len(chunk_ids) == 3


def test_vector_upserter_when_trace_provided_then_record_stage() -> None:
    """应记录 vector_upserter 阶段。"""

    settings = _build_settings()
    trace = TraceContext()
    upserter = VectorUpserter(settings, vector_store=FakeVectorStore(settings))

    upserter.upsert([_build_chunk("same content")], [[0.1, 0.2]], trace=trace)

    assert trace.stages[-1].name == "vector_upserter"
    assert trace.stages[-1].metadata["record_count"] == 1


def test_vector_upserter_when_vector_count_mismatch_then_raise_readable_error() -> None:
    """chunks 与 dense_vectors 数量不一致时应抛出错误。"""

    settings = _build_settings()
    upserter = VectorUpserter(settings, vector_store=FakeVectorStore(settings))

    try:
        upserter.upsert([_build_chunk("same content")], [])
    except ValueError as error:
        assert "dense vector count mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError for dense vector count mismatch")
