"""DenseEncoder implementation built on top of libs.embedding providers."""

from __future__ import annotations

from core.settings import Settings
from core.trace import TraceContext
from core.types import Chunk
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory


class DenseEncoder:
    """Encode chunk text into dense vectors using the configured embedding backend."""

    def __init__(self, settings: Settings, embedding: BaseEmbedding | None = None) -> None:
        self._settings = settings
        self._embedding = embedding
        self._resolved_embedding = embedding

    def encode(
        self,
        chunks: list[Chunk],
        trace: TraceContext | None = None,
    ) -> list[list[float]]:
        """Encode chunks into dense vectors while preserving order."""

        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        vectors = self._get_embedding().embed(texts, trace=trace)

        if len(vectors) != len(chunks):
            raise ValueError(
                f"dense vector count mismatch: expected {len(chunks)}, got {len(vectors)}"
            )

        expected_dim: int | None = None
        for index, vector in enumerate(vectors):
            if not isinstance(vector, list):
                raise TypeError(f"dense vector at index {index} must be list[float]")
            if expected_dim is None:
                expected_dim = len(vector)
            elif len(vector) != expected_dim:
                raise ValueError(
                    f"dense vector dimension mismatch at index {index}: "
                    f"expected {expected_dim}, got {len(vector)}"
                )

        if trace is not None:
            trace.record_stage(
                "dense_encoder",
                {"chunk_count": len(chunks), "dimension": expected_dim or 0},
            )

        return vectors

    def _get_embedding(self) -> BaseEmbedding:
        if self._resolved_embedding is None:
            self._resolved_embedding = EmbeddingFactory.create(self._settings)
        return self._resolved_embedding
