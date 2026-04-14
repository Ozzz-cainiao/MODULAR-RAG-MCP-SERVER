"""DocumentChunker 契约测试。"""

from __future__ import annotations

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.types import Chunk, Document
from ingestion.chunking.document_chunker import DocumentChunker
from libs.splitter.base_splitter import BaseSplitter
from libs.splitter.splitter_factory import SplitterFactory


class FakeSplitter(BaseSplitter):
    """用于隔离测试的 Fake Splitter。"""

    def __init__(self, settings: Settings, chunks: list[str]) -> None:
        super().__init__(settings)
        self._chunks = chunks

    def split_text(self, text: str, trace: object | None = None) -> list[str]:
        return list(self._chunks)


def _build_settings(provider: str = "fake") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider="azure_openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider=provider),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_document_chunker_split_document_when_fake_splitter_then_build_chunks_with_metadata() -> None:
    """应把文本列表转换为 Chunk，并继承元数据。"""

    chunks = ["第一段", "第二段"]
    settings = _build_settings()
    SplitterFactory.register("fake", lambda s: FakeSplitter(s, chunks))

    document = Document(
        id="doc-001",
        text="第一段第二段",
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
    )

    result = DocumentChunker(settings).split_document(document)

    assert [item.text for item in result] == chunks
    assert all(isinstance(item, Chunk) for item in result)
    assert all(item.source_ref == "doc-001" for item in result)
    assert [item.metadata["chunk_index"] for item in result] == [0, 1]
    assert all(item.metadata["source_path"] == "path/sample.pdf" for item in result)
    assert all(item.metadata["doc_type"] == "pdf" for item in result)
    assert all(item.metadata["title"] == "样例" for item in result)


def test_document_chunker_split_document_when_called_twice_then_chunk_ids_stable() -> None:
    """同一文档重复切分应生成稳定的 Chunk ID。"""

    chunks = ["稳定文本", "稳定文本二"]
    settings = _build_settings()
    SplitterFactory.register("fake", lambda s: FakeSplitter(s, chunks))

    document = Document(
        id="doc-xyz",
        text="稳定文本稳定文本二",
        metadata={"source_path": "path/sample.pdf", "doc_type": "pdf", "title": "样例"},
    )

    chunker = DocumentChunker(settings)
    first = chunker.split_document(document)
    second = chunker.split_document(document)

    assert [item.id for item in first] == [item.id for item in second]
    assert len(set(item.id for item in first)) == len(first)
