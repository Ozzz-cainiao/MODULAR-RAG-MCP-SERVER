"""VectorUpserter for stable-id dense vector persistence."""

from __future__ import annotations

import hashlib

from core.trace import TraceContext
from core.types import Chunk
from libs.vector_store.base_vector_store import BaseVectorStore, VectorRecord
from libs.vector_store.vector_store_factory import VectorStoreFactory


class VectorUpserter:
    """Prepare vector records with deterministic chunk ids and upsert them."""

    def __init__(self, settings, vector_store: BaseVectorStore | None = None) -> None:
        self._settings = settings
        self._vector_store = vector_store
        self._resolved_vector_store = vector_store

    def upsert(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        trace: TraceContext | None = None,
    ) -> list[str]:
        """Upsert dense vectors and return stable chunk ids in input order."""

        if len(chunks) != len(dense_vectors):
            raise ValueError(
                f"dense vector count mismatch: expected {len(chunks)}, got {len(dense_vectors)}"
            )

        records: list[VectorRecord] = []
        chunk_ids: list[str] = []
        for index, (chunk, vector) in enumerate(zip(chunks, dense_vectors)):
            chunk_id = self._build_chunk_id(chunk, index)
            metadata = dict(chunk.metadata)
            metadata["source_ref"] = chunk.source_ref
            metadata["start_offset"] = chunk.start_offset
            metadata["end_offset"] = chunk.end_offset
            records.append(
                {
                    "chunk_id": chunk_id,
                    "vector": vector,
                    "text": chunk.text,
                    "metadata": metadata,
                }
            )
            chunk_ids.append(chunk_id)

        self._get_vector_store().upsert(records, trace=trace)

        if trace is not None:
            trace.record_stage(
                "vector_upserter",
                {"record_count": len(records)},
            )

        return chunk_ids

    def _build_chunk_id(self, chunk: Chunk, index: int) -> str:
        source_path = str(chunk.metadata["source_path"])
        content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()[:8]
        raw = f"{source_path}:{index}:{content_hash}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"chunk_{digest}"

    def _get_vector_store(self) -> BaseVectorStore:
        if self._resolved_vector_store is None:
            self._resolved_vector_store = VectorStoreFactory.create(self._settings)
        return self._resolved_vector_store
