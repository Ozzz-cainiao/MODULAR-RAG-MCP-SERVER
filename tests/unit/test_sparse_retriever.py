"""Unit tests for SparseRetriever."""

from __future__ import annotations

from core.query_engine.sparse_retriever import SparseRetriever
from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from core.trace import TraceContext
from core.types import ProcessedQuery
from ingestion.storage.bm25_indexer import BM25QueryResult
from libs.vector_store.base_vector_store import BaseVectorStore


class FakeBM25Indexer:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int]] = []

    def query(self, keywords: list[str], top_k: int = 5):
        self.calls.append((keywords, top_k))
        return [
            BM25QueryResult(chunk_id="chunk-2", score=2.5),
            BM25QueryResult(chunk_id="chunk-1", score=1.5),
        ]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.calls: list[tuple[list[str], object]] = []

    def upsert(self, records, trace=None) -> None:
        raise NotImplementedError

    def query(self, vector, top_k, filters=None, trace=None):
        raise NotImplementedError

    def get_by_ids(self, chunk_ids, trace=None):
        self.calls.append((chunk_ids, trace))
        return [
            {
                "chunk_id": "chunk-2",
                "score": 0.0,
                "text": "bm25 best match",
                "metadata": {"source_path": "doc-b.md", "doc_type": "md", "title": "B"},
            },
            {
                "chunk_id": "chunk-1",
                "score": 0.0,
                "text": "second match",
                "metadata": {
                    "source_path": "doc-a.md",
                    "doc_type": "md",
                    "title": "A",
                    "collection": "docs",
                },
            },
        ]


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_sparse_retriever_when_hits_found_then_hydrate_and_preserve_bm25_order() -> None:
    settings = _build_settings()
    bm25_indexer = FakeBM25Indexer()
    vector_store = FakeVectorStore(settings)
    retriever = SparseRetriever(settings, bm25_indexer=bm25_indexer, vector_store=vector_store)
    trace = TraceContext()

    results = retriever.search(
        ProcessedQuery(original_query="azure", keywords=["azure"], filters={}),
        top_k=2,
        trace=trace,
    )

    assert [result.chunk_id for result in results] == ["chunk-2", "chunk-1"]
    assert [result.score for result in results] == [2.5, 1.5]
    assert bm25_indexer.calls == [(["azure"], 2)]
    assert vector_store.calls == [(["chunk-2", "chunk-1"], trace)]
    assert trace.stages[-1].name == "sparse_retrieval"


def test_sparse_retriever_when_filters_present_then_apply_them_after_hydration() -> None:
    settings = _build_settings()
    retriever = SparseRetriever(
        settings,
        bm25_indexer=FakeBM25Indexer(),
        vector_store=FakeVectorStore(settings),
    )

    results = retriever.search(
        ProcessedQuery(
            original_query="azure collection:docs",
            keywords=["azure"],
            filters={"collection": "docs"},
        )
    )

    assert [result.chunk_id for result in results] == ["chunk-1"]
