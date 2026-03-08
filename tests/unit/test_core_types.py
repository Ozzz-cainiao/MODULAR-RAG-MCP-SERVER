"""核心数据类型契约测试。"""

from __future__ import annotations

import json

import pytest

from core.types import (
    Chunk,
    ChunkRecord,
    Document,
    build_image_placeholder,
    parse_image_placeholders,
)


def test_document_roundtrip_when_metadata_valid_then_serializable_and_stable() -> None:
    """验证 Document 可稳定序列化与反序列化。"""

    image_id = "doc_hash_1_0"
    document = Document(
        id="doc-1",
        text=f"这是正文。{build_image_placeholder(image_id)}",
        metadata={
            "source_path": "tests/fixtures/sample_documents/sample.md",
            "images": [
                {
                    "id": image_id,
                    "path": f"data/images/test/{image_id}.png",
                    "page": 1,
                    "text_offset": 5,
                    "text_length": len(build_image_placeholder(image_id)),
                    "position": {"x": 0, "y": 0, "width": 100, "height": 80},
                }
            ],
        },
    )

    payload = document.to_dict()
    encoded = document.to_json()
    decoded = Document.from_json(encoded)

    assert list(payload.keys()) == ["id", "text", "metadata"]
    assert parse_image_placeholders(document.text) == [image_id]
    assert json.loads(encoded)["id"] == "doc-1"
    assert decoded == document


def test_document_init_when_source_path_missing_then_raise_error() -> None:
    """缺失 source_path 时应抛出可读错误。"""

    with pytest.raises(ValueError, match="metadata.source_path"):
        Document(id="doc-1", text="hello", metadata={})


def test_document_init_when_images_schema_invalid_then_raise_error() -> None:
    """metadata.images 字段不合法时应抛出可读错误。"""

    with pytest.raises(ValueError, match="metadata.images\\[0\\]\\.text_offset"):
        Document(
            id="doc-1",
            text="hello",
            metadata={
                "source_path": "tests/fixtures/sample_documents/sample.md",
                "images": [
                    {
                        "id": "img-1",
                        "path": "data/images/test/img-1.png",
                        "text_offset": -1,
                        "text_length": 10,
                    }
                ],
            },
        )


def test_chunk_roundtrip_when_offsets_valid_then_keep_contract() -> None:
    """验证 Chunk 的偏移与序列化契约。"""

    chunk = Chunk(
        id="chunk-1",
        text="段落内容",
        metadata={"source_path": "tests/fixtures/sample_documents/sample.md"},
        start_offset=10,
        end_offset=20,
        source_ref="doc-1",
    )

    payload = chunk.to_dict()
    restored = Chunk.from_dict(payload)

    assert list(payload.keys()) == ["id", "text", "metadata", "start_offset", "end_offset", "source_ref"]
    assert restored == chunk


def test_chunk_init_when_end_offset_less_than_start_offset_then_raise_error() -> None:
    """结束偏移小于起始偏移时应抛出错误。"""

    with pytest.raises(ValueError, match="end_offset"):
        Chunk(
            id="chunk-1",
            text="段落内容",
            metadata={"source_path": "tests/fixtures/sample_documents/sample.md"},
            start_offset=20,
            end_offset=10,
        )


def test_chunk_record_roundtrip_when_vectors_valid_then_serializable() -> None:
    """验证 ChunkRecord 向量字段契约。"""

    record = ChunkRecord(
        id="record-1",
        text="段落内容",
        metadata={"source_path": "tests/fixtures/sample_documents/sample.md"},
        dense_vector=[1, 2.5, 3],
        sparse_vector={"rag": 0.7, "mcp": 0.3},
    )

    payload = record.to_dict()
    restored = ChunkRecord.from_json(record.to_json())

    assert list(payload.keys()) == ["id", "text", "metadata", "dense_vector", "sparse_vector"]
    assert payload["dense_vector"] == [1.0, 2.5, 3.0]
    assert restored == record


def test_chunk_record_init_when_sparse_vector_value_not_number_then_raise_error() -> None:
    """稀疏向量值类型不合法时应抛出错误。"""

    with pytest.raises(TypeError, match="sparse_vector"):
        ChunkRecord(
            id="record-1",
            text="段落内容",
            metadata={"source_path": "tests/fixtures/sample_documents/sample.md"},
            sparse_vector={"rag": "bad-value"},  # type: ignore[arg-type]
        )
