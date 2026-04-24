"""Query preprocessing helpers."""

from __future__ import annotations

import re

from core.types import ProcessedQuery


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")
_FILTER_PATTERN = re.compile(
    r"(?P<key>collection|doc_type|source_path|title|page):(?P<value>[^\s]+)",
    flags=re.IGNORECASE,
)


class QueryProcessor:
    """Extract keywords and structured filters from a user query."""

    def process(self, query: str) -> ProcessedQuery:
        """Normalize the raw query into keywords and metadata filters."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")

        normalized_query = query.strip()
        filters: dict[str, object] = {}
        stripped_query = normalized_query

        for match in _FILTER_PATTERN.finditer(normalized_query):
            key = match.group("key").lower()
            raw_value = match.group("value").strip()
            value: object = int(raw_value) if key == "page" and raw_value.isdigit() else raw_value
            filters[key] = value
            stripped_query = stripped_query.replace(match.group(0), " ")

        keywords = [token.lower() for token in _TOKEN_PATTERN.findall(stripped_query)]
        if not keywords:
            fallback_terms = []
            for value in filters.values():
                fallback_terms.extend(_TOKEN_PATTERN.findall(str(value)))
            keywords = [token.lower() for token in fallback_terms]

        if not keywords:
            raise ValueError("query 必须包含可检索关键词")

        return ProcessedQuery(
            original_query=normalized_query,
            keywords=keywords,
            filters=filters,
        )
