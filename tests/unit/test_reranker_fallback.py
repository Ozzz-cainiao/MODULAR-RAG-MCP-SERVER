"""Unit tests for core reranker orchestration."""

from __future__ import annotations

from core.query_engine.reranker import Reranker
from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from core.trace import TraceContext
from core.types import RetrievalResult
from libs.reranker.base_reranker import BaseReranker


class FailingReranker(BaseReranker):
    def rerank(self, query: str, candidates: list[dict], trace=None) -> list[dict]:
        raise RuntimeError("backend unavailable")


class ReverseReranker(BaseReranker):
    def rerank(self, query: str, candidates: list[dict], trace=None) -> list[dict]:
        return list(reversed(candidates))


def _build_settings(provider: str = "none") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider=provider),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def _candidate(chunk_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        text=f"text-{chunk_id}",
        metadata={"source_path": f"{chunk_id}.md", "doc_type": "md", "title": chunk_id},
    )


def test_reranker_when_backend_succeeds_then_return_ranked_results() -> None:
    reranker = Reranker(_build_settings("custom"), backend=ReverseReranker(_build_settings("custom")))

    results = reranker.rerank("query", [_candidate("c1", 0.9), _candidate("c2", 0.8)])

    assert [item.chunk_id for item in results] == ["c2", "c1"]


def test_reranker_when_backend_fails_then_fallback_to_original_order_and_trace() -> None:
    trace = TraceContext()
    reranker = Reranker(_build_settings("llm"), backend=FailingReranker(_build_settings("llm")))

    results = reranker.rerank(
        "query",
        [_candidate("c1", 0.9), _candidate("c2", 0.8)],
        trace=trace,
    )

    assert [item.chunk_id for item in results] == ["c1", "c2"]
    assert results[0].metadata["rerank_fallback"] == "original_order"
    assert trace.stages[-1].name == "rerank"
    assert "fallback_reason" in trace.stages[-1].metadata
