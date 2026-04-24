"""Unit tests for QueryProcessor."""

from __future__ import annotations

import pytest

from core.query_engine.query_processor import QueryProcessor


def test_query_processor_when_query_has_filters_then_extract_keywords_and_filters() -> None:
    processor = QueryProcessor()

    result = processor.process("如何配置 Azure collection:docs page:2")

    assert result.keywords == ["如何配置", "azure"]
    assert result.filters == {"collection": "docs", "page": 2}


def test_query_processor_when_query_only_has_filters_then_use_filter_values_as_keywords() -> None:
    processor = QueryProcessor()

    result = processor.process("collection:knowledge title:RAG指南")

    assert result.keywords == ["knowledge", "rag", "指南"]
    assert result.filters["collection"] == "knowledge"
    assert result.filters["title"] == "RAG指南"


def test_query_processor_when_query_empty_then_raise() -> None:
    processor = QueryProcessor()

    with pytest.raises(ValueError, match="非空字符串"):
        processor.process("   ")
