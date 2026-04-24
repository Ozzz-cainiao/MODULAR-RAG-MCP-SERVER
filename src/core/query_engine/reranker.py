"""Core reranker orchestration with graceful fallback."""

from __future__ import annotations

from core.settings import Settings
from core.trace import TraceContext
from core.types import RetrievalResult
from libs.reranker.base_reranker import BaseReranker
from libs.reranker.reranker_factory import RerankerFactory


class Reranker:
    """Wrap the provider reranker and normalize fallback behavior."""

    def __init__(self, settings: Settings, backend: BaseReranker | None = None) -> None:
        self._settings = settings
        self._backend = backend or RerankerFactory.create(settings)

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int | None = None,
        trace: TraceContext | None = None,
    ) -> list[RetrievalResult]:
        """Rerank candidates and fall back to original order on failure."""

        limit = top_k or len(candidates)
        candidate_payloads = [candidate.to_dict() for candidate in candidates]

        fallback_reason: str | None = None
        try:
            ranked_payloads = self._backend.rerank(query=query, candidates=candidate_payloads, trace=trace)
            results = [RetrievalResult.from_dict(payload) for payload in ranked_payloads[:limit]]
        except Exception as error:
            fallback_reason = str(error)
            results = [
                RetrievalResult(
                    chunk_id=candidate.chunk_id,
                    score=candidate.score,
                    text=candidate.text,
                    metadata={**candidate.metadata, "rerank_fallback": "original_order"},
                )
                for candidate in candidates[:limit]
            ]

        if trace is not None:
            metadata = {
                "method": "rerank",
                "provider": self._settings.rerank.provider,
                "input_count": len(candidates),
                "result_count": len(results),
            }
            if fallback_reason is not None:
                metadata["fallback_reason"] = fallback_reason
            trace.record_stage("rerank", metadata)

        return results
