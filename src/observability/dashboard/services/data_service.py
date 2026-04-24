"""Dashboard data access helpers."""

from __future__ import annotations

from core.settings import Settings
from ingestion.document_manager import DocumentManager
from ingestion.storage.image_storage import ImageStorage
from libs.vector_store.chroma_store import ChromaStore


class DataService:
    def __init__(
        self,
        settings: Settings,
        document_manager: DocumentManager | None = None,
        chroma_store: ChromaStore | None = None,
        image_storage: ImageStorage | None = None,
    ) -> None:
        self._document_manager = document_manager or DocumentManager(settings)
        self._chroma_store = chroma_store or ChromaStore(settings)
        self._image_storage = image_storage or ImageStorage()

    def list_documents(self, collection: str | None = None):
        return self._document_manager.list_documents(collection=collection)

    def get_document_detail(self, doc_id: str):
        return self._document_manager.get_document_detail(doc_id)

    def list_chunks(self, source_path: str | None = None, collection: str | None = None):
        filters: dict[str, object] = {}
        if source_path is not None:
            filters["source_path"] = source_path
        if collection is not None:
            filters["collection"] = collection
        return self._chroma_store.get_by_metadata(filters or None)

    def list_images(self, collection: str | None = None, doc_hash: str | None = None):
        return self._image_storage.list_images(collection=collection, doc_hash=doc_hash)
