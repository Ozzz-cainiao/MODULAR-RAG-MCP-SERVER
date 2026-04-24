"""Unit tests for reciprocal rank fusion."""

from __future__ import annotations

from core.query_engine.fusion import ReciprocalRankFusion
from core.types import RetrievalResult


def _result(chunk_id: str, score: float, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        metadata={"source_path": f"{chunk_id}.md", "doc_type": "md", "title": chunk_id},
    )


def test_rrf_when_dense_and_sparse_overlap_then_accumulate_scores() -> None:
    fusion = ReciprocalRankFusion(k=10)

    results = fusion.fuse(
        dense_results=[_result("c1", 0.9, "dense-1"), _result("c2", 0.8, "dense-2")],
        sparse_results=[_result("c2", 1.2, "sparse-2"), _result("c3", 1.1, "sparse-3")],
        top_k=3,
    )

    assert [item.chunk_id for item in results] == ["c2", "c1", "c3"]
    assert results[0].score > results[1].score


def test_rrf_when_top_k_smaller_then_truncate() -> None:
    fusion = ReciprocalRankFusion()

    results = fusion.fuse(
        dense_results=[_result("c1", 1.0, "one"), _result("c2", 0.9, "two")],
        sparse_results=[_result("c3", 1.0, "three")],
        top_k=2,
    )

    assert len(results) == 2
