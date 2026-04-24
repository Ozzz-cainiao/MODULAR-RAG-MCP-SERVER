"""Unit tests for DocumentManager."""

from __future__ import annotations

from pathlib import Path

from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from ingestion.document_manager import DocumentManager
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage
from libs.loader.file_integrity import SQLiteIntegrityChecker
from libs.vector_store.chroma_store import ChromaStore


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_document_manager_list_and_delete_document(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(tmp_path / "chroma"))
    settings = _build_settings()
    chroma = ChromaStore(settings)
    chroma.upsert(
        [
            {
                "chunk_id": "chunk-1",
                "vector": [1.0],
                "text": "hello",
                "metadata": {
                    "source_path": "/tmp/sample.pdf",
                    "collection": "docs",
                    "source_ref": "doc-001",
                    "doc_type": "pdf",
                    "title": "Sample",
                },
            }
        ]
    )
    bm25 = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    bm25._documents = {"chunk-1": {"source_ref": "doc-001", "sparse_vector": {"hello": 1.0}, "doc_length": 1}}
    bm25._rebuild_postings()
    bm25.save()
    image_storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(tmp_path / "db" / "image_index.db"),
    )
    image_storage.save_image("img-1", b"img", "docs", doc_hash="doc-001")
    integrity = SQLiteIntegrityChecker(db_path=str(tmp_path / "db" / "ingestion_history.db"))
    integrity.mark_success("hash-1", "/tmp/sample.pdf")

    manager = DocumentManager(
        settings,
        chroma_store=chroma,
        bm25_indexer=bm25,
        image_storage=image_storage,
        file_integrity=integrity,
    )

    documents = manager.list_documents()
    assert len(documents) == 1
    assert documents[0].chunk_count == 1

    result = manager.delete_document("/tmp/sample.pdf", "docs")
    assert result.deleted_chunks == 1
    assert manager.list_documents() == []
