"""Unit tests for the list_collections MCP tool."""

from __future__ import annotations

from pathlib import Path

from mcp_server.tools.list_collections import list_collections


def test_list_collections_when_directories_exist_then_return_sorted_collection_names(
    tmp_path: Path,
) -> None:
    docs_root = tmp_path / "documents"
    (docs_root / "alpha").mkdir(parents=True)
    (docs_root / "beta").mkdir(parents=True)
    (docs_root / "alpha" / "a.md").write_text("a", encoding="utf-8")
    (docs_root / "beta" / "b.md").write_text("b", encoding="utf-8")
    (docs_root / "beta" / "nested").mkdir()
    (docs_root / "beta" / "nested" / "c.md").write_text("c", encoding="utf-8")

    result = list_collections(documents_root=str(docs_root))

    assert [item["name"] for item in result["structuredContent"]["collections"]] == ["alpha", "beta"]
    assert result["structuredContent"]["collections"][1]["document_count"] == 2


def test_list_collections_when_root_missing_then_return_empty_result(tmp_path: Path) -> None:
    result = list_collections(documents_root=str(tmp_path / "missing"))

    assert result["structuredContent"]["collections"] == []
    assert "暂无可用集合" in result["content"][0]["text"]
