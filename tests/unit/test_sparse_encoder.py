"""Unit tests for SparseEncoder."""

from __future__ import annotations

from core.trace import TraceContext
from core.types import Chunk
from ingestion.embedding.sparse_encoder import SparseEncoder


def _build_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        metadata={"source_path": "sample.pdf", "doc_type": "pdf", "title": "样例"},
        start_offset=0,
        end_offset=len(text),
        source_ref="doc-001",
    )


def test_sparse_encoder_encode_when_text_has_repeated_terms_then_return_normalized_weights() -> None:
    """重复 term 应得到归一化权重。"""

    encoder = SparseEncoder()

    vectors = encoder.encode([_build_chunk("chunk-1", "RAG rag MCP")])

    assert vectors == [{"mcp": 1 / 3, "rag": 2 / 3}]


def test_sparse_encoder_encode_when_text_contains_chinese_then_keep_chinese_tokens() -> None:
    """中文 term 应被保留到稀疏向量。"""

    encoder = SparseEncoder()

    vectors = encoder.encode([_build_chunk("chunk-1", "机器学习 机器学习 检索增强")])

    assert vectors == [{"机器学习": 2 / 3, "检索增强": 1 / 3}]


def test_sparse_encoder_encode_when_text_empty_then_return_empty_mapping() -> None:
    """空文本应返回空稀疏向量。"""

    encoder = SparseEncoder()

    vectors = encoder.encode([_build_chunk("chunk-1", "   \n\t  ")])

    assert vectors == [{}]


def test_sparse_encoder_encode_when_multiple_chunks_then_preserve_input_order() -> None:
    """多个 chunk 编码结果应保持输入顺序。"""

    encoder = SparseEncoder()
    chunks = [
        _build_chunk("chunk-1", "alpha beta"),
        _build_chunk("chunk-2", "gamma gamma"),
    ]

    vectors = encoder.encode(chunks)

    assert vectors[0] == {"alpha": 0.5, "beta": 0.5}
    assert vectors[1] == {"gamma": 1.0}


def test_sparse_encoder_encode_when_trace_provided_then_record_stage() -> None:
    """Trace 应记录 sparse_encoder 阶段。"""

    encoder = SparseEncoder()
    trace = TraceContext()

    encoder.encode(
        [
            _build_chunk("chunk-1", "alpha beta"),
            _build_chunk("chunk-2", ""),
        ],
        trace=trace,
    )

    assert trace.stages[-1].name == "sparse_encoder"
    assert trace.stages[-1].metadata["chunk_count"] == 2
    assert trace.stages[-1].metadata["non_empty_vectors"] == 1
