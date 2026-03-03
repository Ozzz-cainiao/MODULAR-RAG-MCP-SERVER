"""ChromaStore roundtrip 集成测试。"""

from __future__ import annotations

from pathlib import Path

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.vector_store.chroma_store import ChromaStore
from libs.vector_store.vector_store_factory import VectorStoreFactory


def _build_settings(provider: str = "chroma") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider=provider),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_chroma_store_roundtrip_when_upsert_and_query_then_result_is_deterministic(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """覆盖 upsert→query roundtrip、top_k、filters 与持久化重载。"""

    persist_dir = tmp_path / "chroma"
    monkeypatch.setenv("CHROMA_PERSIST_PATH", str(persist_dir))

    settings = _build_settings("chroma")
    store = VectorStoreFactory.create(settings)

    assert isinstance(store, ChromaStore)

    store.upsert(
        [
            {
                "chunk_id": "doc-1",
                "vector": [1.0, 0.0],
                "text": "alpha document",
                "metadata": {"collection": "docs", "source": "spec"},
            },
            {
                "chunk_id": "doc-2",
                "vector": [0.8, 0.2],
                "text": "beta document",
                "metadata": {"collection": "docs", "source": "guide"},
            },
            {
                "chunk_id": "faq-1",
                "vector": [0.0, 1.0],
                "text": "faq answer",
                "metadata": {"collection": "faq", "source": "faq"},
            },
        ]
    )

    query_results = store.query(
        vector=[1.0, 0.0],
        top_k=2,
        filters={"collection": "docs"},
    )

    assert len(query_results) == 2
    assert [item["chunk_id"] for item in query_results] == ["doc-1", "doc-2"]
    assert all(item["metadata"]["collection"] == "docs" for item in query_results)
    assert query_results[0]["score"] >= query_results[1]["score"]

    reloaded_store = VectorStoreFactory.create(settings)
    reloaded_results = reloaded_store.query(
        vector=[1.0, 0.0],
        top_k=1,
        filters={"collection": "docs"},
    )

    assert len(reloaded_results) == 1
    assert reloaded_results[0]["chunk_id"] == "doc-1"
    assert (persist_dir / "records.json").exists()

