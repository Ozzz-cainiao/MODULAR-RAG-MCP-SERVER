"""Unit tests for get_document_summary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.tools.get_document_summary import get_document_summary


def test_get_document_summary_when_doc_exists_then_return_structured_summary(tmp_path: Path) -> None:
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    (chroma_dir / "records.json").write_text(
        json.dumps(
            [
                {
                    "chunk_id": "chunk-1",
                    "vector": [1.0],
                    "text": "Azure deployment guide section one.",
                    "metadata": {
                        "source_ref": "doc-001",
                        "source_path": "guide.md",
                        "doc_type": "md",
                        "title": "Azure Guide",
                        "collection": "docs",
                    },
                },
                {
                    "chunk_id": "chunk-2",
                    "vector": [0.5],
                    "text": "Section two with more details.",
                    "metadata": {
                        "source_ref": "doc-001",
                        "source_path": "guide.md",
                        "doc_type": "md",
                        "title": "Azure Guide",
                        "collection": "docs",
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    result = get_document_summary("doc-001", chroma_persist_path=str(chroma_dir))

    assert result["structuredContent"]["doc_id"] == "doc-001"
    assert result["structuredContent"]["title"] == "Azure Guide"
    assert "Azure deployment guide" in result["structuredContent"]["summary"]


def test_get_document_summary_when_doc_missing_then_raise_readable_error(tmp_path: Path) -> None:
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    (chroma_dir / "records.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="未找到 doc_id"):
        get_document_summary("doc-404", chroma_persist_path=str(chroma_dir))
