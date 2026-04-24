"""E2E recall regression using the golden set."""

from __future__ import annotations

from pathlib import Path

from core.query_engine import DenseRetriever, HybridSearch, QueryProcessor, ReciprocalRankFusion, SparseRetriever
from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from ingestion.storage.bm25_indexer import BM25Indexer
from libs.embedding.base_embedding import BaseEmbedding
from libs.vector_store.vector_store_factory import VectorStoreFactory
from observability.evaluation import EvalRunner


class FakeEmbedding(BaseEmbedding):
    def embed(self, texts: list[str], trace=None) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=3),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_recall_when_running_golden_set_then_hit_rate_meets_threshold(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("BM25_PERSIST_PATH", str(tmp_path / "bm25"))
    settings = _build_settings()
    store = VectorStoreFactory.create(settings)
    store.upsert(
        [
            {
                "chunk_id": "chunk-1",
                "vector": [1.0, 0.0],
                "text": "Azure deployment guide",
                "metadata": {"source_path": "guide.md", "doc_type": "md", "title": "Guide"},
            }
        ]
    )
    bm25 = BM25Indexer(persist_dir=str(tmp_path / "bm25"))
    bm25._documents = {
        "chunk-1": {
            "text": "Azure deployment guide",
            "metadata": {},
            "source_ref": "doc-001",
            "sparse_vector": {"azure": 0.5, "deployment": 0.5},
            "doc_length": 2,
        }
    }
    bm25._rebuild_postings()
    bm25.save()
    hybrid = HybridSearch(
        settings,
        query_processor=QueryProcessor(),
        dense_retriever=DenseRetriever(settings, embedding=FakeEmbedding(settings), vector_store=store),
        sparse_retriever=SparseRetriever(settings, bm25_indexer=bm25, vector_store=store),
        fusion=ReciprocalRankFusion(),
    )
    report = EvalRunner(settings, hybrid).run(str(Path("tests/fixtures/golden_test_set.json")))

    assert report.hit_rate >= 1.0
