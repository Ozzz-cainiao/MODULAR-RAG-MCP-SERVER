"""Integration tests for hybrid search orchestration."""

from __future__ import annotations

from pathlib import Path

from core.query_engine import (
    DenseRetriever,
    HybridSearch,
    QueryProcessor,
    ReciprocalRankFusion,
    Reranker,
    SparseRetriever,
)
from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from core.trace import TraceContext
from ingestion.storage.bm25_indexer import BM25Indexer
from libs.embedding.base_embedding import BaseEmbedding
from libs.vector_store.vector_store_factory import VectorStoreFactory


class FakeEmbedding(BaseEmbedding):
    def embed(self, texts: list[str], trace=None) -> list[list[float]]:
        query = texts[0].lower()
        if "azure" in query:
            return [[1.0, 0.0]]
        return [[0.0, 1.0]]


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=3),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_hybrid_search_when_dense_and_sparse_both_hit_then_return_fused_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(tmp_path / "chroma"))
    settings = _build_settings()
    vector_store = VectorStoreFactory.create(settings)
    vector_store.upsert(
        [
            {
                "chunk_id": "chunk-1",
                "vector": [1.0, 0.0],
                "text": "Azure deployment guide",
                "metadata": {
                    "source_path": "azure.md",
                    "doc_type": "md",
                    "title": "Azure Guide",
                    "collection": "docs",
                },
            },
            {
                "chunk_id": "chunk-2",
                "vector": [0.8, 0.2],
                "text": "Azure auth notes",
                "metadata": {
                    "source_path": "auth.md",
                    "doc_type": "md",
                    "title": "Auth Notes",
                    "collection": "docs",
                },
            },
            {
                "chunk_id": "chunk-3",
                "vector": [0.0, 1.0],
                "text": "Kubernetes operations",
                "metadata": {
                    "source_path": "k8s.md",
                    "doc_type": "md",
                    "title": "K8s",
                    "collection": "ops",
                },
            },
        ]
    )
    bm25 = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    bm25._documents = {
        "chunk-1": {
            "text": "Azure deployment guide",
            "metadata": {"collection": "docs"},
            "sparse_vector": {"azure": 0.5, "deployment": 0.5},
            "doc_length": 2,
        },
        "chunk-2": {
            "text": "Azure auth notes",
            "metadata": {"collection": "docs"},
            "sparse_vector": {"azure": 0.5, "auth": 0.5},
            "doc_length": 2,
        },
    }
    bm25._rebuild_postings()
    bm25.save()

    hybrid = HybridSearch(
        settings,
        query_processor=QueryProcessor(),
        dense_retriever=DenseRetriever(settings, embedding=FakeEmbedding(settings), vector_store=vector_store),
        sparse_retriever=SparseRetriever(settings, bm25_indexer=bm25, vector_store=vector_store),
        fusion=ReciprocalRankFusion(k=10),
    )
    trace = TraceContext(trace_type="query")

    result = hybrid.search("如何配置 Azure", collection="docs", trace=trace)
    reranked = Reranker(settings).rerank("如何配置 Azure", result.fused_results, trace=trace)

    assert result.processed_query.filters["collection"] == "docs"
    assert [item.chunk_id for item in result.fused_results] == ["chunk-1", "chunk-2"]
    assert [item.chunk_id for item in reranked] == ["chunk-1", "chunk-2"]
    assert trace.trace_type == "query"
    assert [stage.name for stage in trace.stages] == [
        "query_processing",
        "dense_retrieval",
        "sparse_retrieval",
        "fusion",
        "rerank",
    ]
    for stage in trace.stages:
        assert "elapsed_ms" in stage.metadata
