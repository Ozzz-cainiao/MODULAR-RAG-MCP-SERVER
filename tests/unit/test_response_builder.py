"""Unit tests for MCP response building."""

from __future__ import annotations

import base64
from pathlib import Path

from core.response import MultimodalAssembler, ResponseBuilder
from core.types import RetrievalResult
from ingestion.storage.image_storage import ImageStorage


def _result(text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id="chunk-1",
        score=0.9,
        text=text,
        metadata={"source_path": "guide.md", "doc_type": "md", "title": "Guide", "page": 3},
    )


def test_response_builder_when_results_exist_then_return_markdown_and_citations() -> None:
    builder = ResponseBuilder()

    result = builder.build([_result("Azure deployment guide")], query="Azure")

    assert result["content"][0]["type"] == "text"
    assert "[1]" in result["content"][0]["text"]
    assert result["structuredContent"]["citations"][0]["chunk_id"] == "chunk-1"


def test_response_builder_when_image_placeholder_exists_then_append_image_content(tmp_path: Path) -> None:
    image_storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(tmp_path / "image_index.db"),
    )
    image_path = image_storage.save_image(
        image_id="img-001",
        image_bytes=b"fake-image",
        collection="docs",
        doc_hash="doc-001",
    )
    assert Path(image_path).exists()

    builder = ResponseBuilder(
        multimodal_assembler=MultimodalAssembler(image_storage=image_storage)
    )

    result = builder.build([_result("Result with [IMAGE: img-001]")], query="image")

    assert len(result["content"]) == 2
    assert result["content"][1]["type"] == "image"
    assert result["content"][1]["mimeType"] == "image/png"
    assert base64.b64decode(result["content"][1]["data"]) == b"fake-image"


def test_response_builder_when_results_empty_then_return_friendly_message() -> None:
    builder = ResponseBuilder()

    result = builder.build([], query="missing")

    assert "未找到" in result["content"][0]["text"]
    assert result["structuredContent"]["citations"] == []
