"""BatchProcessor implementation for dense and sparse encoding orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from core.trace import TraceContext
from core.types import Chunk, SparseVector
from ingestion.embedding.dense_encoder import DenseEncoder
from ingestion.embedding.sparse_encoder import SparseEncoder


@dataclass(slots=True)
class BatchResult:
    """Aggregated encoding results for a processed chunk list."""

    dense_vectors: list[list[float]]
    sparse_vectors: list[SparseVector]


class BatchProcessor:
    """Split chunks into batches and run dense/sparse encoding in stable order."""

    def __init__(
        self,
        dense_encoder: DenseEncoder,
        sparse_encoder: SparseEncoder,
        batch_size: int = 32,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

        self._dense_encoder = dense_encoder
        self._sparse_encoder = sparse_encoder
        self._batch_size = batch_size

    def process(
        self,
        chunks: list[Chunk],
        trace: TraceContext | None = None,
    ) -> BatchResult:
        """Process chunks in batches and aggregate dense/sparse outputs."""

        dense_vectors: list[list[float]] = []
        sparse_vectors: list[SparseVector] = []

        for batch_index, batch in enumerate(self._iter_batches(chunks)):
            started_at = perf_counter()
            batch_dense = self._dense_encoder.encode(batch, trace=trace)
            batch_sparse = self._sparse_encoder.encode(batch, trace=trace)
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)

            dense_vectors.extend(batch_dense)
            sparse_vectors.extend(batch_sparse)

            if trace is not None:
                trace.record_stage(
                    "batch_processor",
                    {
                        "batch_index": batch_index,
                        "batch_size": len(batch),
                        "elapsed_ms": elapsed_ms,
                    },
                )

        return BatchResult(dense_vectors=dense_vectors, sparse_vectors=sparse_vectors)

    def _iter_batches(self, chunks: list[Chunk]) -> list[list[Chunk]]:
        return [
            chunks[index : index + self._batch_size]
            for index in range(0, len(chunks), self._batch_size)
        ]
