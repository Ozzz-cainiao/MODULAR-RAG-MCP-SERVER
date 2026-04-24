"""Sparse retrieval orchestration."""

from __future__ import annotations

from time import perf_counter

from core.settings import Settings
from core.trace import TraceContext
from core.types import ProcessedQuery, RetrievalResult
from ingestion.storage.bm25_indexer import BM25Indexer
from libs.vector_store.base_vector_store import BaseVectorStore
from libs.vector_store.vector_store_factory import VectorStoreFactory


class SparseRetriever:
    """Retrieve sparse candidates from BM25 and hydrate from the vector store."""

    def __init__(
        self,
        settings: Settings,
        bm25_indexer: BM25Indexer | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self._settings = settings
        self._bm25_indexer = bm25_indexer or BM25Indexer()
        self._vector_store = vector_store or VectorStoreFactory.create(settings)

    def search(
        self,
        query: ProcessedQuery,
        top_k: int | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """Return BM25 candidates enriched with stored text and metadata."""

        limit = top_k or self._settings.retrieval.top_k
        stage_started = perf_counter()
        ranked = self._bm25_indexer.query(query.keywords, top_k=limit)
        hydrated = self._vector_store.get_by_ids([result.chunk_id for result in ranked], trace=trace)
        hydrated_by_id = {payload["chunk_id"]: payload for payload in hydrated}

        results: list[RetrievalResult] = []
        for candidate in ranked:
            payload = hydrated_by_id.get(candidate.chunk_id)
            if payload is None:
                continue
            metadata = dict(payload["metadata"])
            if query.filters and not _match_filters(metadata, query.filters):
                continue
            results.append(
                RetrievalResult(
                    chunk_id=candidate.chunk_id,
                    score=candidate.score,
                    text=str(payload["text"]),
                    metadata=metadata,
                )
            )

        if trace is not None:
            trace.record_stage(
                "sparse_retrieval",
                {
                    "method": "bm25",
                    "provider": "bm25",
                    "keywords": list(query.keywords),
                    "filters": dict(query.filters),
                    "result_count": len(results),
                    "elapsed_ms": round((perf_counter() - stage_started) * 1000, 3),
                },
            )
        return results


def _match_filters(metadata: dict[str, object], filters: dict[str, object]) -> bool:
    for key, value in filters.items():
        if metadata.get(key) != value:
            return False
    return True
