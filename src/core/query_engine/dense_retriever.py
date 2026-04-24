"""Dense retrieval orchestration."""

from __future__ import annotations

from core.settings import Settings
from core.trace import TraceContext
from core.types import ProcessedQuery, RetrievalResult
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.vector_store.base_vector_store import BaseVectorStore
from libs.vector_store.vector_store_factory import VectorStoreFactory


class DenseRetriever:
    """Retrieve dense candidates from the configured vector store."""

    def __init__(
        self,
        settings: Settings,
        embedding: BaseEmbedding | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self._settings = settings
        self._embedding = embedding or EmbeddingFactory.create(settings)
        self._vector_store = vector_store or VectorStoreFactory.create(settings)

    def search(
        self,
        query: ProcessedQuery,
        top_k: int | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """Return dense retrieval results for the processed query."""

        limit = top_k or self._settings.retrieval.top_k
        vectors = self._embedding.embed([" ".join(query.keywords)], trace=trace)
        if len(vectors) != 1:
            raise ValueError(f"dense query vector count mismatch: expected 1, got {len(vectors)}")

        payloads = self._vector_store.query(
            vector=vectors[0],
            top_k=limit,
            filters=dict(query.filters) or None,
            trace=trace,
        )
        results = [RetrievalResult.from_dict(payload) for payload in payloads]

        if trace is not None:
            trace.record_stage(
                "dense_retrieval",
                {
                    "method": "vector_search",
                    "provider": self._settings.vector_store.provider,
                    "query_text": " ".join(query.keywords),
                    "filters": dict(query.filters),
                    "result_count": len(results),
                },
            )
        return results
