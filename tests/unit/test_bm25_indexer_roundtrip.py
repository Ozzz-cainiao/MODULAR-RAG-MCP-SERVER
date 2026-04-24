"""Unit tests for BM25Indexer build, persistence, and query roundtrip."""

from __future__ import annotations

from math import isclose, log
from pathlib import Path

from core.types import Chunk
from ingestion.embedding.sparse_encoder import SparseEncoder
from ingestion.storage.bm25_indexer import BM25Indexer


def _build_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={"source_path": "sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=len(text),
        source_ref="doc-001",
    )


def test_bm25_indexer_roundtrip_when_build_save_load_query_then_results_stable(tmp_path: Path) -> None:
    """build/save/load/query roundtrip 后应返回稳定结果。"""

    chunks = [
        _build_chunk("chunk-1", "rag retrieval pipeline"),
        _build_chunk("chunk-2", "bm25 sparse retrieval"),
        _build_chunk("chunk-3", "vision caption"),
    ]
    sparse_vectors = SparseEncoder().encode(chunks)
    indexer = BM25Indexer(persist_dir=str(tmp_path / "bm25"))

    indexer.build(chunks, sparse_vectors)
    reloaded = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    reloaded.load()
    results = reloaded.query(["retrieval"], top_k=2)

    assert [result.chunk_id for result in results] == ["chunk-1", "chunk-2"]
    assert results[0].score == results[1].score


def test_bm25_indexer_when_build_then_idf_matches_formula(tmp_path: Path) -> None:
    """IDF 计算应符合规范公式。"""

    chunks = [
        _build_chunk("chunk-1", "alpha beta"),
        _build_chunk("chunk-2", "alpha gamma"),
        _build_chunk("chunk-3", "delta"),
    ]
    indexer = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    indexer.build(chunks, SparseEncoder().encode(chunks))

    indexer.load()
    alpha_idf = indexer._postings["alpha"]["idf"]
    expected = log((3 - 2 + 0.5) / (2 + 0.5))
    assert isclose(alpha_idf, expected, rel_tol=1e-9)


def test_bm25_indexer_when_incremental_build_then_merge_new_documents(tmp_path: Path) -> None:
    """增量构建应保留旧文档并加入新文档。"""

    persist_dir = str(tmp_path / "bm25")
    initial_chunks = [_build_chunk("chunk-1", "alpha beta")]
    new_chunks = [_build_chunk("chunk-2", "beta gamma")]
    indexer = BM25Indexer(persist_dir=persist_dir)

    indexer.build(initial_chunks, SparseEncoder().encode(initial_chunks))
    indexer.build(new_chunks, SparseEncoder().encode(new_chunks), incremental=True)

    reloaded = BM25Indexer(persist_dir=persist_dir)
    reloaded.load()
    results = reloaded.query("beta", top_k=5)

    assert [result.chunk_id for result in results] == ["chunk-1", "chunk-2"]


def test_bm25_indexer_when_sparse_vector_count_mismatch_then_raise_readable_error(tmp_path: Path) -> None:
    """chunks 与 sparse_vectors 数量不一致时应抛出错误。"""

    indexer = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    chunks = [_build_chunk("chunk-1", "alpha beta")]

    try:
        indexer.build(chunks, [])
    except ValueError as error:
        assert "sparse vector count mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError for sparse vector count mismatch")
