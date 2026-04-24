"""E2E tests for the query CLI entry point."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import query


class FakeHybridSearch:
    def __init__(self, settings) -> None:
        self.settings = settings

    def search(self, query: str, top_k=None, collection=None, trace=None):
        from core.query_engine.hybrid_search import HybridSearchResult
        from core.types import ProcessedQuery, RetrievalResult

        if "empty" in query:
            return HybridSearchResult(
                processed_query=ProcessedQuery(original_query=query, keywords=["empty"], filters={}),
                dense_results=[],
                sparse_results=[],
                fused_results=[],
            )

        result = RetrievalResult(
            chunk_id="chunk-1",
            score=0.9,
            text="Azure deployment guide",
            metadata={"source_path": "azure.md", "doc_type": "md", "title": "Azure", "page": 1},
        )
        return HybridSearchResult(
            processed_query=ProcessedQuery(original_query=query, keywords=["azure"], filters={}),
            dense_results=[result],
            sparse_results=[result],
            fused_results=[result],
        )


class FakeReranker:
    def __init__(self, settings) -> None:
        self.settings = settings

    def rerank(self, query: str, candidates: list, top_k=None, trace=None):
        return list(candidates[: top_k or len(candidates)])


def test_query_cli_when_hits_found_then_print_results(monkeypatch, capsys) -> None:
    monkeypatch.setattr(query, "HybridSearch", FakeHybridSearch)
    monkeypatch.setattr(query, "Reranker", FakeReranker)

    exit_code = query.main(["--query", "如何配置 Azure", "--verbose"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[Dense]" in output
    assert "[Top-K]" in output
    assert "Azure deployment guide" in output


def test_query_cli_when_no_data_then_print_friendly_message(monkeypatch, capsys) -> None:
    monkeypatch.setattr(query, "HybridSearch", FakeHybridSearch)
    monkeypatch.setattr(query, "Reranker", FakeReranker)

    exit_code = query.main(["--query", "empty"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "未找到相关文档" in output
