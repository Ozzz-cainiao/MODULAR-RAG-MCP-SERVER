"""Unit tests for DenseRetriever."""

from __future__ import annotations

from core.query_engine.dense_retriever import DenseRetriever
from core.settings import ObservabilitySettings, ProviderSettings, RetrievalSettings, Settings
from core.trace import TraceContext
from core.types import ProcessedQuery
from libs.embedding.base_embedding import BaseEmbedding
from libs.vector_store.base_vector_store import BaseVectorStore


class FakeEmbedding(BaseEmbedding):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.calls: list[tuple[list[str], object]] = []

    def embed(self, texts: list[str], trace=None) -> list[list[float]]:
        self.calls.append((texts, trace))
        return [[0.9, 0.1]]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.last_query: tuple[list[float], int, dict[str, object] | None, object] | None = None

    def upsert(self, records, trace=None) -> None:
        raise NotImplementedError

    def query(self, vector, top_k, filters=None, trace=None):
        self.last_query = (vector, top_k, filters, trace)
        return [
            {
                "chunk_id": "chunk-1",
                "score": 0.88,
                "text": "azure setup guide",
                "metadata": {"source_path": "guide.md", "doc_type": "md", "title": "Guide"},
            }
        ]

    def get_by_ids(self, chunk_ids, trace=None):
        raise NotImplementedError


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


def test_dense_retriever_when_query_valid_then_return_retrieval_results() -> None:
    settings = _build_settings()
    embedding = FakeEmbedding(settings)
    vector_store = FakeVectorStore(settings)
    retriever = DenseRetriever(settings, embedding=embedding, vector_store=vector_store)
    processed_query = ProcessedQuery(
        original_query="如何配置 Azure",
        keywords=["azure", "配置"],
        filters={"collection": "docs"},
    )
    trace = TraceContext()

    results = retriever.search(processed_query, top_k=3, trace=trace)

    assert len(results) == 1
    assert results[0].chunk_id == "chunk-1"
    assert embedding.calls[0][0] == ["azure 配置"]
    assert vector_store.last_query == ([0.9, 0.1], 3, {"collection": "docs"}, trace)
    assert trace.stages[-1].name == "dense_retrieval"


def test_dense_retriever_when_embedding_returns_wrong_count_then_raise() -> None:
    settings = _build_settings()

    class BrokenEmbedding(FakeEmbedding):
        def embed(self, texts: list[str], trace=None) -> list[list[float]]:
            return [[0.1], [0.2]]

    retriever = DenseRetriever(
        settings,
        embedding=BrokenEmbedding(settings),
        vector_store=FakeVectorStore(settings),
    )

    try:
        retriever.search(
            ProcessedQuery(original_query="test", keywords=["test"], filters={}),
        )
    except ValueError as error:
        assert "dense query vector count mismatch" in str(error)
    else:
        raise AssertionError("Expected vector count mismatch error")
