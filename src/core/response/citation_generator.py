"""Citation helpers for MCP responses."""

from __future__ import annotations

from core.types import RetrievalResult


class CitationGenerator:
    """Generate structured citations from retrieval results."""

    def generate(self, retrieval_results: list[RetrievalResult]) -> list[dict[str, object]]:
        """Return normalized citations in result order."""

        citations: list[dict[str, object]] = []
        for index, result in enumerate(retrieval_results, start=1):
            metadata = result.metadata
            citations.append(
                {
                    "index": index,
                    "chunk_id": result.chunk_id,
                    "score": result.score,
                    "source": metadata.get("source_path", "unknown"),
                    "page": metadata.get("page"),
                }
            )
        return citations
