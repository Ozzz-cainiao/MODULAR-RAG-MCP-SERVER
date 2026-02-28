"""Vector Store 契约测试。"""

from __future__ import annotations

from typing import Any

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.vector_store.base_vector_store import (
    BaseVectorStore,
    TraceContext,
    VectorQueryResult,
    VectorRecord,
)
from libs.vector_store.vector_store_factory import VectorStoreFactory


class FakeVectorStore(BaseVectorStore):
    """用于契约测试的 Fake Vector Store。"""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._records: list[VectorRecord] = []

    def upsert(self, records: list[VectorRecord], trace: TraceContext | None = None) -> None:
        """写入记录并校验输入 shape。"""

        required_keys = {"chunk_id", "vector", "text", "metadata"}
        for record in records:
            if not required_keys.issubset(record.keys()):
                raise ValueError("record 缺少必填键: chunk_id/vector/text/metadata")
            if not isinstance(record["vector"], list):
                raise ValueError("record.vector 必须是 list[float]")

        self._records.extend(records)

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按简单相似度返回结果并保证输出 shape。"""

        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")

        filtered_records = self._records
        if filters is not None and "collection" in filters:
            collection = filters["collection"]
            filtered_records = [
                record
                for record in self._records
                if isinstance(record.get("metadata"), dict)
                and record["metadata"].get("collection") == collection
            ]

        def score_of(record: VectorRecord) -> float:
            stored = record["vector"]
            if len(stored) != len(vector):
                return -1.0
            return float(sum(left * right for left, right in zip(stored, vector)))

        ranked = sorted(filtered_records, key=score_of, reverse=True)[:top_k]

        return [
            {
                "chunk_id": item["chunk_id"],
                "score": score_of(item),
                "text": item["text"],
                "metadata": item["metadata"],
            }
            for item in ranked
        ]


def _build_settings(provider: str) -> Settings:
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


def test_vector_store_contract_when_upsert_and_query_then_output_matches_shape() -> None:
    """验证 upsert/query 的输入输出契约 shape。"""

    provider = "fake-vector-b4"
    VectorStoreFactory.register(provider, FakeVectorStore)
    settings = _build_settings(provider)
    store = VectorStoreFactory.create(settings)

    store.upsert(
        [
            {
                "chunk_id": "c1",
                "vector": [1.0, 0.0],
                "text": "chunk one",
                "metadata": {"collection": "docs"},
            },
            {
                "chunk_id": "c2",
                "vector": [0.5, 0.5],
                "text": "chunk two",
                "metadata": {"collection": "docs"},
            },
        ]
    )

    results = store.query(vector=[1.0, 0.0], top_k=2, filters={"collection": "docs"})

    assert len(results) == 2
    for item in results:
        assert set(["chunk_id", "score", "text", "metadata"]).issubset(item.keys())
        assert isinstance(item["chunk_id"], str)
        assert isinstance(item["score"], float)
        assert isinstance(item["text"], str)
        assert isinstance(item["metadata"], dict)


def test_vector_store_contract_when_upsert_missing_required_keys_then_raise_error() -> None:
    """缺少必填键时应抛出可读错误。"""

    provider = "fake-vector-b4-shape"
    VectorStoreFactory.register(provider, FakeVectorStore)
    settings = _build_settings(provider)
    store = VectorStoreFactory.create(settings)

    with pytest.raises(ValueError, match="必填键"):
        store.upsert([{"chunk_id": "c1", "vector": [1.0, 0.0]}])


def test_vector_store_factory_create_when_provider_missing_then_raise_readable_error() -> None:
    """未注册 provider 时应抛出可读错误。"""

    settings = _build_settings("not-registered-vector-store")

    with pytest.raises(ValueError, match="not-registered-vector-store"):
        VectorStoreFactory.create(settings)

