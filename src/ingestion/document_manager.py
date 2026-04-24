"""Cross-storage document management helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.settings import Settings
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore


@dataclass(slots=True)
class DocumentInfo:
    source_path: str
    collection: str
    chunk_count: int
    image_count: int
    document_id: str | None


@dataclass(slots=True)
class DeleteResult:
    source_path: str
    deleted_chunks: int
    deleted_images: int
    deleted_history: int


class DocumentManager:
    """Coordinate document-level operations across storage backends."""

    def __init__(
        self,
        settings: Settings,
        chroma_store: ChromaStore | None = None,
        bm25_indexer: BM25Indexer | None = None,
        image_storage: ImageStorage | None = None,
        file_integrity: SQLiteIntegrityChecker | None = None,
    ) -> None:
        self._chroma_store = chroma_store or ChromaStore(settings)
        self._bm25_indexer = bm25_indexer or BM25Indexer()
        self._image_storage = image_storage or ImageStorage()
        self._file_integrity = file_integrity or SQLiteIntegrityChecker()

    def list_documents(self, collection: str | None = None) -> list[DocumentInfo]:
        records = self._chroma_store.get_by_metadata(
            {"collection": collection} if collection is not None else None
        )
        grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
        for record in records:
            metadata = record["metadata"]
            source_path = str(metadata.get("source_path", "unknown"))
            record_collection = str(metadata.get("collection", "default"))
            grouped.setdefault((source_path, record_collection), []).append(record)

        results: list[DocumentInfo] = []
        for (source_path, record_collection), items in sorted(grouped.items()):
            document_id = items[0]["metadata"].get("source_ref")
            image_count = len(
                self._image_storage.list_images(
                    collection=record_collection,
                    doc_hash=str(document_id) if isinstance(document_id, str) else None,
                )
            )
            results.append(
                DocumentInfo(
                    source_path=source_path,
                    collection=record_collection,
                    chunk_count=len(items),
                    image_count=image_count,
                    document_id=str(document_id) if isinstance(document_id, str) else None,
                )
            )
        return results

    def get_document_detail(self, doc_id: str) -> dict[str, object]:
        matches = self._chroma_store.get_by_metadata()
        related = [
            record
            for record in matches
            if isinstance(record.get("metadata"), dict) and record["metadata"].get("source_ref") == doc_id
        ]
        if not related:
            raise ValueError(f"未找到文档: {doc_id}")

        first_metadata = dict(related[0]["metadata"])
        return {
            "doc_id": doc_id,
            "title": first_metadata.get("title", doc_id),
            "source_path": first_metadata.get("source_path"),
            "collection": first_metadata.get("collection"),
            "chunks": related,
            "images": self._image_storage.list_images(
                collection=first_metadata.get("collection"),
                doc_hash=doc_id,
            ),
        }

    def delete_document(self, source_path: str, collection: str) -> DeleteResult:
        records = self._chroma_store.get_by_metadata({"source_path": source_path, "collection": collection})
        document_ids = {
            str(record["metadata"].get("source_ref"))
            for record in records
            if isinstance(record.get("metadata"), dict) and record["metadata"].get("source_ref")
        }
        deleted_chunks = self._chroma_store.delete_by_metadata(
            {"source_path": source_path, "collection": collection}
        )

        deleted_images = 0
        for document_id in document_ids:
            images = self._image_storage.list_images(collection=collection, doc_hash=document_id)
            for image in images:
                file_path = Path(str(image["file_path"]))
                if file_path.exists():
                    file_path.unlink()
                deleted_images += 1
            self._bm25_indexer.remove_document(document_id)

        deleted_history = self._file_integrity.remove_record(source_path)
        return DeleteResult(
            source_path=source_path,
            deleted_chunks=deleted_chunks,
            deleted_images=deleted_images,
            deleted_history=deleted_history,
        )

    def get_collection_stats(self, collection: str | None = None) -> dict[str, object]:
        documents = self.list_documents(collection=collection)
        total_chunks = sum(document.chunk_count for document in documents)
        total_images = sum(document.image_count for document in documents)
        return {
            "collection": collection,
            "document_count": len(documents),
            "chunk_count": total_chunks,
            "image_count": total_images,
        }
