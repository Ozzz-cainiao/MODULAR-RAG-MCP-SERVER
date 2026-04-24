"""Hybrid search orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from core.query_engine.dense_retriever import DenseRetriever
from core.query_engine.fusion import ReciprocalRankFusion
from core.query_engine.query_processor import QueryProcessor
from core.query_engine.sparse_retriever import SparseRetriever
from core.settings import Settings
from core.trace import TraceContext
from core.types import ProcessedQuery, RetrievalResult


@dataclass(slots=True)
class HybridSearchResult:
    """Structured hybrid search output with debug-friendly intermediates."""

    processed_query: ProcessedQuery
    dense_results: list[RetrievalResult]
    sparse_results: list[RetrievalResult]
    fused_results: list[RetrievalResult]


class HybridSearch:
    """Run query processing, dense retrieval, sparse retrieval, and fusion."""

    def __init__(
        self,
        settings: Settings,
        query_processor: QueryProcessor | None = None,
        dense_retriever: DenseRetriever | None = None,
        sparse_retriever: SparseRetriever | None = None,
        fusion: ReciprocalRankFusion | None = None,
    ) -> None:
        self._settings = settings
        self._query_processor = query_processor or QueryProcessor()
        self._dense_retriever = dense_retriever or DenseRetriever(settings)
        self._sparse_retriever = sparse_retriever or SparseRetriever(settings)
        self._fusion = fusion or ReciprocalRankFusion()

    def search(
        self,
        query: str,
        top_k: int | None = None,
        collection: str | None = None,
        trace: TraceContext | None = None,
    ) -> HybridSearchResult:
        """Run the full hybrid retrieval pipeline."""

        processed_query = self._query_processor.process(query)
        if collection is not None:
            processed_query.filters["collection"] = collection

        limit = top_k or self._settings.retrieval.top_k
        if trace is not None:
            trace.record_stage(
                "query_processing",
                {
                    "method": "keyword_filter_extraction",
                    "query": processed_query.original_query,
                    "keywords": list(processed_query.keywords),
                    "filters": dict(processed_query.filters),
                },
            )

        dense_results: list[RetrievalResult]
        sparse_results: list[RetrievalResult]
        dense_error: str | None = None
        sparse_error: str | None = None

        try:
            dense_results = self._dense_retriever.search(processed_query, top_k=limit, trace=trace)
        except Exception as error:
            dense_results = []
            dense_error = str(error)

        try:
            sparse_results = self._sparse_retriever.search(processed_query, top_k=limit, trace=trace)
        except Exception as error:
            sparse_results = []
            sparse_error = str(error)

        if dense_error is not None and sparse_error is not None:
            raise RuntimeError(
                "hybrid search failed: "
                f"dense={dense_error}; sparse={sparse_error}"
            )

        if dense_results and sparse_results:
            fused_results = self._fusion.fuse(dense_results, sparse_results, top_k=limit)
        else:
            fused_results = list((dense_results or sparse_results)[:limit])

        if trace is not None:
            metadata = {
                "method": "rrf" if dense_results and sparse_results else "single_path_fallback",
                "provider": "rrf" if dense_results and sparse_results else "fallback",
                "dense_count": len(dense_results),
                "sparse_count": len(sparse_results),
                "result_count": len(fused_results),
            }
            if dense_error is not None:
                metadata["dense_error"] = dense_error
            if sparse_error is not None:
                metadata["sparse_error"] = sparse_error
            trace.record_stage("fusion", metadata)

        return HybridSearchResult(
            processed_query=processed_query,
            dense_results=dense_results,
            sparse_results=sparse_results,
            fused_results=fused_results,
        )
