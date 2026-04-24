"""Result fusion strategies for hybrid retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from core.types import RetrievalResult


@dataclass(slots=True)
class ReciprocalRankFusion:
    """Simple RRF implementation."""

    k: int = 60

    def fuse(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Merge dense and sparse rankings using reciprocal rank fusion."""

        fused: dict[str, RetrievalResult] = {}
        fused_scores: dict[str, float] = {}

        for results in (dense_results, sparse_results):
            for rank, result in enumerate(results, start=1):
                fused_scores[result.chunk_id] = fused_scores.get(result.chunk_id, 0.0) + (
                    1.0 / (self.k + rank)
                )
                fused.setdefault(result.chunk_id, result)

        ranked = sorted(
            fused.values(),
            key=lambda item: (-fused_scores[item.chunk_id], item.chunk_id),
        )
        return [
            RetrievalResult(
                chunk_id=result.chunk_id,
                score=fused_scores[result.chunk_id],
                text=result.text,
                metadata=result.metadata,
            )
            for result in ranked[:top_k]
        ]
