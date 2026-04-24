"""SparseEncoder implementation for BM25-style term statistics preparation."""

from __future__ import annotations

import re

from core.trace import TraceContext
from core.types import Chunk, SparseVector


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


class SparseEncoder:
    """Encode chunk text into sparse term-weight mappings."""

    def encode(
        self,
        chunks: list[Chunk],
        trace: TraceContext | None = None,
    ) -> list[SparseVector]:
        """Build sparse vectors for chunks while preserving input order."""

        vectors = [self._encode_text(chunk.text) for chunk in chunks]

        if trace is not None:
            trace.record_stage(
                "sparse_encoder",
                {
                    "chunk_count": len(chunks),
                    "non_empty_vectors": sum(1 for vector in vectors if vector),
                },
            )

        return vectors

    def _encode_text(self, text: str) -> SparseVector:
        if not text.strip():
            return {}

        tokens = self._tokenize(text)
        if not tokens:
            return {}

        token_counts: dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        total_terms = sum(token_counts.values())
        return {
            token: count / total_terms
            for token, count in sorted(token_counts.items())
        }

    def _tokenize(self, text: str) -> list[str]:
        normalized = text.lower()
        tokens = _TOKEN_PATTERN.findall(normalized)
        return [token.strip() for token in tokens if token.strip()]
