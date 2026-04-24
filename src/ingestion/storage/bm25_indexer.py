"""BM25 index builder and query helper with pickle-based persistence."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
import os
from pathlib import Path
import pickle
import re
from typing import Any

from core.trace import TraceContext
from core.types import Chunk, SparseVector


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")
_INDEX_FILENAME = "bm25_index.pkl"


@dataclass(slots=True)
class BM25QueryResult:
    """Single BM25 query result."""

    chunk_id: str
    score: float


class BM25Indexer:
    """Build, persist, load, and query a lightweight BM25 index."""

    def __init__(self, persist_dir: str = "data/db/bm25") -> None:
        resolved_persist_dir = os.getenv("BM25_PERSIST_PATH", persist_dir)
        self._persist_dir = Path(resolved_persist_dir)
        self._index_path = self._persist_dir / _INDEX_FILENAME
        self._postings: dict[str, dict[str, Any]] = {}
        self._documents: dict[str, dict[str, Any]] = {}
        self._avg_doc_length: float = 0.0

    def build(
        self,
        chunks: list[Chunk],
        sparse_vectors: list[SparseVector],
        trace: TraceContext | None = None,
        incremental: bool = False,
    ) -> None:
        """Build or incrementally update the BM25 index from sparse vectors."""

        if len(chunks) != len(sparse_vectors):
            raise ValueError(
                f"sparse vector count mismatch: expected {len(chunks)}, got {len(sparse_vectors)}"
            )

        documents = self._documents.copy() if incremental and self._index_path.exists() else {}
        if incremental and self._index_path.exists():
            self.load()
            documents = self._documents.copy()

        for chunk, sparse_vector in zip(chunks, sparse_vectors):
            documents[chunk.id] = {
                "text": chunk.text,
                "metadata": chunk.metadata,
                "sparse_vector": sparse_vector,
                "doc_length": self._document_length(chunk.text),
            }

        self._documents = documents
        self._rebuild_postings()
        self.save()

        if trace is not None:
            trace.record_stage(
                "bm25_indexer",
                {
                    "document_count": len(self._documents),
                    "term_count": len(self._postings),
                    "incremental": incremental,
                },
            )

    def save(self) -> None:
        """Persist the current BM25 index to disk."""

        self._persist_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "postings": self._postings,
            "documents": self._documents,
            "avg_doc_length": self._avg_doc_length,
        }
        with self._index_path.open("wb") as handle:
            pickle.dump(payload, handle)

    def load(self) -> None:
        """Load the BM25 index from disk."""

        with self._index_path.open("rb") as handle:
            payload = pickle.load(handle)

        self._postings = dict(payload["postings"])
        self._documents = dict(payload["documents"])
        self._avg_doc_length = float(payload["avg_doc_length"])

    def query(self, keywords: list[str] | str, top_k: int = 5) -> list[BM25QueryResult]:
        """Query the BM25 index with keywords and return ranked chunk ids."""

        if not self._postings:
            if self._index_path.exists():
                self.load()
            else:
                return []

        terms = self._normalize_query_terms(keywords)
        if not terms:
            return []

        scores: dict[str, float] = {}
        avg_doc_length = self._avg_doc_length or 1.0
        k1 = 1.5
        b = 0.75

        for term in terms:
            entry = self._postings.get(term)
            if not entry:
                continue
            idf = float(entry["idf"])
            postings = entry["postings"]
            for posting in postings:
                tf = float(posting["tf"])
                doc_length = int(posting["doc_length"]) or 1
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
                score = idf * (numerator / denominator)
                chunk_id = str(posting["chunk_id"])
                scores[chunk_id] = scores.get(chunk_id, 0.0) + score

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [BM25QueryResult(chunk_id=chunk_id, score=score) for chunk_id, score in ranked[:top_k]]

    def remove_document(self, source_ref: str) -> int:
        """Remove indexed chunks for a document source_ref/doc id."""

        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError("source_ref 必须是非空字符串")

        removed_ids = [
            chunk_id
            for chunk_id, payload in self._documents.items()
            if payload.get("source_ref") == source_ref or payload.get("doc_hash") == source_ref
        ]
        if not removed_ids:
            return 0

        for chunk_id in removed_ids:
            self._documents.pop(chunk_id, None)

        self._rebuild_postings()
        self.save()
        return len(removed_ids)

    def _rebuild_postings(self) -> None:
        postings: dict[str, dict[str, Any]] = {}
        document_count = len(self._documents)
        total_doc_length = 0

        for chunk_id, payload in self._documents.items():
            sparse_vector = payload["sparse_vector"]
            doc_length = int(payload["doc_length"])
            total_doc_length += doc_length

            for term, tf in sparse_vector.items():
                entry = postings.setdefault(term, {"idf": 0.0, "postings": []})
                entry["postings"].append(
                    {
                        "chunk_id": chunk_id,
                        "tf": float(tf),
                        "doc_length": doc_length,
                    }
                )

        self._avg_doc_length = (total_doc_length / document_count) if document_count else 0.0
        for term, entry in postings.items():
            df = len(entry["postings"])
            entry["idf"] = log((document_count - df + 0.5) / (df + 0.5))
            entry["postings"] = sorted(entry["postings"], key=lambda item: item["chunk_id"])

        self._postings = dict(sorted(postings.items()))

    def _document_length(self, text: str) -> int:
        tokens = _TOKEN_PATTERN.findall(text.lower())
        return len(tokens) or 1

    def _normalize_query_terms(self, keywords: list[str] | str) -> list[str]:
        if isinstance(keywords, str):
            query = keywords
        else:
            query = " ".join(keywords)
        return [token for token in _TOKEN_PATTERN.findall(query.lower()) if token]
